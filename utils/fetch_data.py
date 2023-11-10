# %%
import requests
import json
from bs4 import BeautifulSoup
import subprocess
import os
import re
import traceback
from datetime import datetime
from collections import defaultdict

from notion_db import fetch_my_table, update_char_list

CHECKPOINT_OK = "data/char_checkpoint.json"
CHECKPOINT_PENDING = "data/char_pending.json"
DATA_FILE = "data/char_data.json"
DATA_FILE_MIN = "data/char_data_min.json"
ALIAS_FILE = "data/alias.json"

# %%


class Updater:
    def __init__(self, pending: dict, checkpoint: dict, alias: dict, ver: str) -> None:
        self.data = checkpoint.copy()
        self.pending = pending.copy()
        self.template = checkpoint | pending
        self.alias = alias
        self.ver = ver
        self.session = requests.Session()

        print("Fetching notion table")
        self.my_table = fetch_my_table()
        # for "ver" and "id"
        print("Fetching hhw table")
        self.hhw_table = fetch_hhw_table()
        # for "name_en", "url_name", "rarity", "weapon", "element", 
        for k, char in self.template.items():
            if char.get("name_en") is None:
                char["name_en"] = self.hhw_table[k]["name_en"]
            if k in self.my_table:
                char["ver"] = self.my_table[k]["ver"]
                char["id"] = self.my_table[k]["id"]
                # overwrite id (old chars slightly different from official)
            else:
                char["ver"] = self.ver

        self.alias_keys = defaultdict(list)
        # key is name_zh, an alias may map to multiple keys
        for name, char in self.template.items():
            self.alias_keys[char["name_zh"]].append(name)
            self.alias_keys[char["name_en"]].append(name)
            if name in self.alias:
                for _alias in self.alias[name]["alias_zh"]:
                    self.alias_keys[_alias].append(name)
                for _alias in self.alias[name]["alias_en"]:
                    self.alias_keys[_alias].append(name)

    def _find_quote_targets(self, title, current_key, lang) -> list[str]:
        about = {"en": "About ", "zh": "关于"}
        splitter = {"en": ":", "zh": "·"}
        title = title.replace("」", "").replace("「", "")
        if title.startswith(about[lang]):
            target_name = title.split(splitter[lang])[0]
            target_name = target_name[len(about[lang]) :]
            if target_name in self.alias_keys:
                if current_key not in self.alias_keys[target_name]:
                    # found target, and is not self
                    return self.alias_keys[target_name]

    def _merge_lines(self, lines_zh: list[dict], lines_en: list[dict]) -> list[dict]:
        lines = []
        if len(lines_zh) != len(lines_en):
            raise ValueError(
                f"{len(lines_zh)} ZH and {len(lines_en)} EN lines don't match"
            )
        for i in range(len(lines_zh)):
            if lines_zh[i]["target_id"] == lines_en[i]["target_id"]:
                lines.append({**lines_zh[i], **lines_en[i]})
            else:
                # reordering not implemented
                print(lines_zh[i]["target_id"], lines_en[i]["target_id"])
                print(lines_zh[i]["title_zh"], lines_en[i]["title_en"])
                raise ValueError("Quote targets don't match")
        return lines

    def _fetch_quotes_hhw(self, name_zh, lang="zh") -> list[dict]:
        """
        get lines from *char* to other chars
        """
        name = self.template[name_zh]["name_" + lang]
        url_name = self.hhw_table[name_zh]["url_name"]

        if lang == "en":
            lang_param = "EN"
        else:
            lang_param = "CHS"

        URL = "https://genshin.honeyhunterworld.com/%s/?lang=%s" % (
            url_name,
            lang_param,
        )

        lines = []

        res = self.session.get(url=URL, timeout=10)
        soup = BeautifulSoup(res.content, "html.parser")

        # check name
        # display_name = soup.find('div', class_='custom_title').get_text()
        # if (display_name != name):
        #     raise ValueError('Name mismatch: expect %s, got %s' % (name, display_name))
        display_name = soup.select_one("h2.wp-block-post-title").get_text()
        if display_name != name:
            raise ValueError("Name mismatch: expect %s, got %s" % (name, display_name))

        quote_section = soup.find("section", id="char_quotes")
        for tr in quote_section.find_all("tr"):
            title = tr.contents[0].get_text()
            title = title.rstrip(" …")
            target_keys = self._find_quote_targets(title, name_zh, lang)

            if target_keys is not None:
                script_str = tr.contents[1].script.string
                regex = re.search('(?<=line":").+?(?=",)', script_str)
                line = regex.group()
                line = line.replace("\\/", "/")
                line = line.encode().decode("unicode-escape")
                line = line.replace("<br>", "\n")
                line = line.replace("<br/>", "\n")
                line = re.sub(re.compile("<[^>]*>"), "", line)
                # fischl: remove color tags

                title = (
                    f"{name} about" + title.removeprefix("About")
                    if lang == "en"
                    else name + title
                )
                for k in target_keys:
                    target_id = self.template[k]["id"]
                    target_name = self.template[k]["name_" + lang]
                    lines.append(
                        {
                            # 'from_'+lang : name,
                            "target_id": target_id,
                            "target_" + lang: target_name,
                            "title_" + lang: title,
                            "content_" + lang: line,
                        }
                    )

        return lines

    def fetch_quotes(self):
        print("Fetching quotes")
        count_pending = len(self.pending)
        print(f"\t{count_pending} pending / {len(self.template)} total")
        # updated char_dict with quotes
        i = 1
        for k in list(self.pending.keys()):
            try:
                lines_zh = self._fetch_quotes_hhw(k, "zh")
                lines_en = self._fetch_quotes_hhw(k, "en")
                print(f"\t{i} / {count_pending}  {k} ({len(lines_zh)})")
                lines = self._merge_lines(lines_zh, lines_en)
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except:
                traceback.print_exc()
            else:
                self.data[k] = self.template[k].copy()
                self.data[k]["lines"] = lines
                del self.pending[k]
            i += 1
        print(f"\t{count_pending - len(self.pending)} updated")
        print(f"\t{len(self.pending)} errors")

    def update_remote_table(self):
        print("Updating notion table")
        new_dict = {}
        for k in self.template:
            if k not in self.my_table:
                new_dict[k] = self.template[k] | self.hhw_table[k]
        data_update = list(new_dict.values())
        update_char_list(data_update)
        print(f"\t{len(data_update)} entries updated")


def fetch_char_api() -> dict[str, dict[str, str]]:
    S = requests.Session()

    res = S.get(url=os.getenv("URL_ZH"), timeout=20)
    data = res.json()
    char_count = data["data"]["total"]
    char_list_zh = data["data"]["list"]
    char_dict = {}
    for i, entry in enumerate(char_list_zh):
        name = entry["title"]
        d = {
            "id": char_count - i,  # last one = 1
            "name_zh": name,
            "name_en": None,
        }
        # order may be slightly different, but remote data should fix it
        for subentry in entry["ext"]:
            if subentry["arrtName"] == "角色-ICON":
                img_url = subentry["value"][0]["url"]
                d["img_url"] = img_url
                break
        char_dict[name] = d
    return char_dict


def fetch_hhw_table():
    char_table_temp = {}
    lang_params = {"zh": "CHS", "en": "EN"}
    for lang, lang_param in lang_params.items():
        URL = "https://genshin.honeyhunterworld.com/fam_chars/?lang=%s" % lang_param
        res = requests.get(url=URL, timeout=10)
        soup = BeautifulSoup(res.content, "html.parser")
        table = soup.select_one("table.genshin_table")
        s = table.script.string
        s = s.replace("\\/", "/")
        s = s.encode().decode("unicode-escape")
        s = re.search("\(\[.*\]\)", s).group()[1:-1]
        rows = s.split("],")
        for r in rows:
            char = {}
            cells = r.strip('[]"').split('","')
            name = re.search(">(.*)<", cells[1]).group(1)
            url_name = re.search("/(.*)/\?", cells[1]).group(1)
            char["url_name"] = url_name
            char["name_" + lang] = name
            for i, k in enumerate(["rarity", "weapon", "element"]):
                char[k] = re.search(">(.*?)<", cells[2 + i]).group(1)
            if url_name in char_table_temp:
                char_table_temp[url_name].update(char)
            else:
                char_table_temp[url_name] = char
    char_table = {char["name_zh"]: char for char in char_table_temp.values()}
    return char_table


def calc_ver():
    ref_ver = os.environ["REF_VER"]
    if ref_ver is None:
        return ""
    ref_date = os.environ["REF_DATE"]
    period = os.environ["PERIOD"]
    offset = os.getenv("VER_ADJUST", "0.0")
    n_offset = int(100 * float(offset))
    dd = (datetime.utcnow() - datetime.fromisoformat(ref_date)).days
    ref_vers = ref_ver.split(".")
    if ref_vers[-1] == "1":
        ref_vers[-1] = "0"
    else:
        ref_vers[-1] = "5"
    n_ref = int("".join(ref_vers))
    n_banners = dd // int(period)

    n = n_ref + n_banners * 5 + n_offset
    v = list(str(n))
    if v[-1] == "0":
        v[-1] = "1"
    if v[-1] == "5":
        v[-1] = "2"
    return ".".join(v)


def main():
    with open(CHECKPOINT_OK) as f:
        char_checkpoint = json.load(f)
    # loaded old data as a list of dicts
    with open(CHECKPOINT_PENDING) as f:
        char_pending = json.load(f)
    # load aliases
    with open(ALIAS_FILE) as f:
        aliases = json.load(f)

    ver = calc_ver()
    time_start = datetime.now()
    if len(char_pending) == 0:
        # start anew
        print(f"Updating for v{ver}")
        print("Fetching mhy api")
        official_dict = fetch_char_api()

        # got current chars, building from it
        char_names = list(official_dict.keys())
        count_total = len(official_dict)
        print(f"\tLast3 {' '.join(char_names[:3])}")

        count_old = len(char_checkpoint)
        if count_total <= count_old:
            print(f"\t{count_total} released / {count_old} saved")
            print("Already up to date")
            return

        char_names_new = char_names[: count_total - count_old]
        print(f"\tNew char {' '.join(char_names_new)}")

        char_pending = official_dict
        char_checkpoint = {}
    else:
        # resume from last checkpoint
        resume = True
        print(f"Retrying for v{ver}")
        print(f"\t{' '.join(list(char_pending.keys()))}")

    updater = Updater(char_pending, char_checkpoint, aliases, ver)

    updater.update_remote_table()
    updater.fetch_quotes()

    with open(CHECKPOINT_PENDING, "w", encoding="utf8") as f:
        json.dump(updater.pending, f, ensure_ascii=False, indent=4)
    with open(CHECKPOINT_OK, "w", encoding="utf8") as f:
        json.dump(updater.data, f, ensure_ascii=False, indent=4)
    print("Wrote checkpoint")

    if len(updater.pending) == 0:
        char_data = list(updater.data.values())
        char_data.sort(key=lambda x: x["id"])
        with open(DATA_FILE, "w", encoding="utf8") as f:
            json.dump(char_data, f, ensure_ascii=False, indent=4)
        with open(DATA_FILE_MIN, "w", encoding="utf8") as f:
            json.dump(char_data, f, ensure_ascii=False, separators=(",", ":"))
        print("Wrote data files")
        commit_msg = (
            f"v{ver} {' '.join([char['name_zh'] for char in char_data if char['ver']==ver])}"
        )
    else:
        commit_msg = f"v{ver} update checkpoint"
    if os.getenv("GITHUB_ACTIONS") is not None:
        print("Committing changes —— " + commit_msg)
        commit_changes(commit_msg)
        send_message(commit_msg)
    else:
        print(f"Commit message: {commit_msg}")
    time_end = datetime.now()
    print(f"Time elapsed: {(time_end - time_start).total_seconds():.0f}s")


def send_message(msg):
    try:
        k1, v1 = os.getenv("PAYLOAD1").split("=")
        payload = {k1: v1, "text": msg}
        r = requests.get(os.getenv("MSG_URL"), params=payload)
    except:
        traceback.print_exc()


def commit_changes(msg):
    author = "github-actions[bot]"
    email = "41898282+github-actions[bot]@users.noreply.github.com"
    subprocess.run(["git", "config", "user.name", author], check=True)
    subprocess.run(["git", "config", "user.email", email], check=True)
    subprocess.run(["git", "commit", "-a", "-m", msg], check=True)
    subprocess.run(["git", "push"], check=True)


# %%
if __name__ == "__main__":
    main()
