#%%
import requests
import json
from bs4 import BeautifulSoup
import subprocess
import os
import traceback
from datetime import date

from notion_db import fetch_char_list, update_char_list

CHECKPOINT_OK = "utils/char_checkpoint.json"
CHECKPOINT_PENDING = "utils/char_pending.json"
DATA_FILE = "utils/char_data.json"
DATA_FILE_MIN = "page/char_data_min.json"

#%%


class Updater:
    def __init__(self, template=None, checkpoint=None, pending=None) -> None:
        if template is not None:
            self.new = True
            self.data = {}
            self.pending = template.copy()
            self.template = template.copy()
        else:
            self.new = False
            self.data = checkpoint.copy()
            self.pending = pending.copy()
            self.template = checkpoint | pending
        self.count_pending = len(self.pending)

    def _find_quote_target(self, title, current_name, lang) -> tuple[str, int]:
        about = {"en": "About ", "zh": "关于"}
        for char in self.template.values():
            name = char["name_" + lang]
            if name != current_name:
                if about[lang] in title and name in title:
                    return name, char["id"]
                if "alias_" + lang in char:
                    for alias in char["alias_" + lang].split(", "):
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
                print(lines_zh[i]["title_zh"], lines_en[i]["title_en"])
                raise ValueError("Quote targets don't match")
        return lines

    def _fetch_quotes_hhw(self, char, lang="zh") -> list[dict]:
        """
        get lines from *char* to other chars
        """
        name = char["name_" + lang]
        if "url_name" in char:
            url_name = char["url_name"]
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

        URL = "https://genshin.honeyhunterworld.com/db/char/%s/?lang=%s" % (
            url_name,
            lang_param,
        )

        lines = []

        S = requests.Session()
        res = S.get(url=URL)
        soup = BeautifulSoup(res.content, "html.parser")

        # check name
        # display_name = soup.find('div', class_='custom_title').get_text()
        # if (display_name != name):
        #     raise ValueError('Name mismatch: expect %s, got %s' % (name, display_name))
        display_name = soup.select_one(".custom_title").get_text()
        if display_name != name:
            raise ValueError("Name mismatch: expect %s, got %s" % (name, display_name))

        quote_start = soup.find("span", id="scroll_quotes")

        ele = quote_start.next_sibling
        while ele is not None and ele.name != "span":
            table = ele.find("table")
            if table is not None:
                tr1, tr2 = table.contents[:2]
                title = tr1.get_text()

                target_name, target_id = self._find_quote_target(title, name, lang)

                if target_name is not None:
                    while (
                        title.endswith("…")
                        or title.endswith("·")
                        or title.endswith(" ")
                    ):
                        title = title[:-1]
                    tr2_str = str(tr2).replace("<br/><color>", "\n")  # fischl
                    tr2 = BeautifulSoup(tr2_str, "html.parser")
                    v = tr2.get_text()

                    if lang == "en":
                        if title[:5] == "About":  # should always be true
                            title = (
                                name + " about" + title[5:]
                            )  # change "About" to lower case
                    else:
                        title = name + title
                    lines.append(
                        {
                            # 'from_'+lang : name,
                            "target_id": target_id,
                            "target_" + lang: target_name,
                            "title_" + lang: title,
                            "content_" + lang: v,
                        }
                    )
            ele = ele.next_sibling

        return lines

    def fetch_quotes(self):
        i = 1
        for char in list(self.pending.values()):
            try:
                lines_zh = self._fetch_quotes_hhw(char, "zh")
                lines_en = self._fetch_quotes_hhw(char, "en")
                print(
                    f"\t{i} / {self.count_pending}  {char['name_zh']} ({len(lines_zh)})"
                )
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


def fetch_char_api() -> dict[str, dict[str, str]]:
    # api from https://ys.mihoyo.com/main/character/mondstadt
    # channelId 150 mondstadt, 151 liyue, 324 inazuma; 152 seems to be all chars, stumbled across
    # alternatively from english / other language website https://genshin.mihoyo.com/en/character/mondstadt
    # 487, 488, 1108 [489 all]
    URL_zh = "https://ys.mihoyo.com/content/ysCn/getContentList?pageSize=100&pageNum=1&channelId=152"
    URL_en = "https://genshin.mihoyo.com/content/yuanshen/getContentList?pageSize=100&pageNum=1&channelId=489"
    # without &order=asc newest first

    S = requests.Session()

    res = S.get(url=URL_zh, timeout=20)
    data = res.json()
    res2 = S.get(url=URL_en, timeout=20)
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
            "name_en": char_list_en[i]["title"],
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


def annotate_template(template, remote_data: list[dict]):
    for char in remote_data:
        if char["name_zh"] in template:
            template[char["name_zh"]].update(char)


def calc_ver(offset):
    n_offset = int(100 * float(offset))
    # 2022-6-1 Wed v2.7.1 (delayed 3 weeks)
    # 1 sub-version per 6 weeks, usually two banners
    dd = (date.today() - date(2022, 6, 1)).days
    n_ref = 270
    # 2.7.1 -> 270
    # 2.7.2 -> 275
    n_sub = dd // 42
    n_half = 1 + dd % 42 // 21
    # first half or second half
    d_half = dd % 21
    # how long since last banner
    n_banner = 5 * (n_half + (d_half >= 14) - 1)
    # allows pre-updating if close to future banner
    n = n_ref + n_sub * 10 + n_banner + n_offset
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
    count_old = len(char_checkpoint)
    count_total = count_old
    print("Fetching remote data")
    char_list_remote = fetch_char_list()
    ver = calc_ver(char_list_remote[0]["ver"])
    print(f"Updating for v{ver}")

    if len(char_pending) == 0:
        # start anew
        print("Fetching mhy api")
        template = fetch_char_api()
        annotate_template(template, char_list_remote)

        # got current chars, building from it
        char_names = list(template.keys())
        count_total = len(template)
        print(f"\tLast3 {' '.join(char_names[:3])}")

        if count_total <= count_old:
            print(f"\t{count_total} released / {count_old} saved")
            print("Already up to date")
            return

        char_names_new = char_names[: count_total - count_old]
        data_bwiki = fetch_data_bwiki(filter=char_names_new)

        data_update = []
        for k in char_names_new:
            template[k]["ver"] = ver
            data_update.append(template[k] | data_bwiki[k])
        updater = Updater(template=template)
        print(f"\tNew char {' '.join(char_names_new)}")
        try:
            print("Updating remote data")
            update_char_list(data_update)
        except:
            traceback.print_exc()
    else:
        # resume from last checkpoint
        print(f"Retrying {' '.join(list(char_pending.keys()))}")
        annotate_template(char_pending, char_list_remote)
        updater = Updater(checkpoint=char_checkpoint, pending=char_pending)

    print(f"Fetching quotes")
    print(f"\t{updater.count_pending} pending / {count_total} total")
    updater.fetch_quotes()
    # updated char_dict with quotes
    print(f"Updated {updater.count_pending - len(updater.pending)} chars")
    print(f"{len(updater.pending)} errors")

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
