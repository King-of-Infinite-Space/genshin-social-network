#%%
import requests
import json
from bs4 import BeautifulSoup
import subprocess
import os
import re
import traceback
from datetime import datetime

from notion_db import fetch_remote_dict, update_char_list

CHECKPOINT_OK = "data/char_checkpoint.json"
CHECKPOINT_PENDING = "data/char_pending.json"
DATA_FILE = "data/char_data.json"
DATA_FILE_MIN = "data/char_data_min.json"
ALIAS_FILE = "data/alias.json"

#%%


class Updater:
    def __init__(self, pending: dict, checkpoint={}, remote={}, alias={}) -> None:
        self.data = checkpoint.copy()
        self.pending = pending.copy()
        self.template = checkpoint | pending
        self.remote = remote
        for k in self.remote:
            self.template[k].update(self.remote[k])
            del self.template[k]["url_name"]
            # i'm using different id from official
        self.alias = alias
        self.session = requests.Session()

    def _find_quote_target(self, title, current_name, lang) -> tuple[str, int]:
        about = {"en": "About ", "zh": "关于"}
        for char in self.template.values():
            name = char["name_" + lang]
            if name != current_name:
                if about[lang] in title and name in title:
                    return name, char["id"]
                if char["name_zh"] in self.alias:
                    for alias in self.alias[char["name_zh"]]["alias_" + lang]:
                        if about[lang] in title and alias in title:
                            return name, char["id"]
        return None, None

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

    def _fetch_quotes_hhw(self, char, lang="zh") -> list[dict]:
        """
        get lines from *char* to other chars
        """
        name = char["name_" + lang]
        name_zh = char["name_zh"]
        if name_zh in self.remote and self.remote[name_zh]["url_name"]:
            url_name = self.remote[name_zh]["url_name"]
        elif len(char["name_zh"]) == len(char["name_en"].split(" ")):
            # 2-char chinese full names, Hu Tao, Yun Jin
            url_name = char["name_en"].replace(" ", "")
        else:
            # single name or japanese given name
            url_name = char["name_en"].split(" ")[-1]

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

            target_name, target_id = self._find_quote_target(title, name, lang)

            if target_name is not None:
                while title.endswith("…") or title.endswith("·") or title.endswith(" "):
                    title = title[:-1]

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
                    f"{name} about {' '.join(title.split(' ')[1:])}"
                    if lang == "en"
                    else name + title
                )
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
        count_pending = len(self.pending)
        print(f"\t{count_pending} pending / {len(self.template)} total")
        # updated char_dict with quotes
        i = 1
        for char in list(self.pending.values()):
            try:
                lines_zh = self._fetch_quotes_hhw(char, "zh")
                lines_en = self._fetch_quotes_hhw(char, "en")
                print(f"\t{i} / {count_pending}  {char['name_zh']} ({len(lines_zh)})")
                lines = self._merge_lines(lines_zh, lines_en)
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except:
                traceback.print_exc()
            else:
                self.data[char["name_zh"]] = self.template[char["name_zh"]].copy()
                self.data[char["name_zh"]]["lines"] = lines
                del self.pending[char["name_zh"]]
            i += 1
        print(f"\t{count_pending - len(self.pending)} updated")
        print(f"\t{len(self.pending)} errors")


def fetch_char_api() -> dict[str, dict[str, str]]:

    S = requests.Session()

    res = S.get(url=os.getenv("URL_ZH"), timeout=20)
    data = res.json()
    res2 = S.get(url=os.getenv("URL_EN"), timeout=20)
    data2 = res2.json()
    char_count = data["data"]["total"]
    char_list_zh = data["data"]["list"]
    char_list_en = data2["data"]["list"]
    if len(char_list_zh) != len(char_list_en):
        raise ValueError(
            f"{len(char_list_zh)} ZH and {len(char_list_en)} EN char data entries don't match"
        )
    char_dict = {}
    for i, entry in enumerate(char_list_zh):
        name = entry["title"]
        d = {
            "id": char_count - i,  # last one = 1
            "name_zh": name,
            "name_en": char_list_en[i]["sTitle"],
        }
        # order may be slightly different, but remote data should fix it
        for subentry in entry["ext"]:
            if subentry["arrtName"] == "角色-ICON":
                img_url = subentry["value"][0]["url"]
                d["img_url"] = img_url
                break
        char_dict[name] = d
    return char_dict


def fetch_data_bwiki(filter=None):
    # https://www.mediawiki.org/wiki/API:Parsing_wikitext
    S = requests.Session()
    URL = "https://wiki.biligame.com/ys/api.php"
    PARAMS = {"action": "parse", "page": "角色筛选", "format": "json"}

    res = S.get(url=URL, params=PARAMS)
    html_doc = res.json()["parse"]["text"]["*"]
    # table = pd.read_html(data, attrs={'id':"CardSelectTr"})
    soup = BeautifulSoup(html_doc, "html.parser")
    table = soup.find(id="CardSelectTr")

    chars = {}
    columns = ["name_zh", "rarity", "weapon", "element", "gender", "region"]
    for tr in table.find_all("tr")[1:]:  # ignore thead
        char = {}
        i = 0
        for td in tr.find_all("td", limit=1 + len(columns))[1:]:  # ignore image
            char[columns[i]] = td.get_text().strip()
            i += 1
        char["rarity"] = int(char["rarity"][0]) if len(char["rarity"]) else None
        char["weapon"] = char["weapon"][0] if len(char["weapon"]) else None
        if filter is None or char["name_zh"] in filter:
            chars[char["name_zh"]] = char
    return chars


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


def update_remote(official_dict, remote_dict, ver):
    names = [k for k in official_dict.keys() if k not in remote_dict.keys()]
    for k in names:
        official_dict[k]["ver"] = ver
    data_bwiki = fetch_data_bwiki(filter=names)
    data_update = [official_dict[k] | data_bwiki[k] for k in names]
    update_char_list(data_update)
    print(f"\t{len(data_update)} entries updated")


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

    print("Fetching remote data")
    remote_dict = fetch_remote_dict()

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

        print("Updating remote data")
        update_remote(official_dict, remote_dict, ver)

        updater = Updater(official_dict, remote=remote_dict, alias=aliases)
    else:
        # resume from last checkpoint
        print(f"Retrying for v{ver}")
        print(f"\t{' '.join(list(char_pending.keys()))}")
        updater = Updater(
            char_pending,
            checkpoint=char_checkpoint,
            remote=remote_dict,
            alias=aliases,
        )

    print(f"Fetching quotes")
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
        commit_msg = f"v{ver} {' '.join([char['name_zh'] for char in char_data if char['ver']==ver])}"
    else:
        commit_msg = f"v{ver} update checkpoint"
    if os.getenv("GITHUB_ACTIONS") is not None:
        print("Committing changes —— " + commit_msg)
        commit_changes(commit_msg)
        send_message(commit_msg)
    else:
        print(f"Commit message: {commit_msg}")


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


#%%
if __name__ == "__main__":
    main()
