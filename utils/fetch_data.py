# %%
import requests
import json
import subprocess
import os
import re
import gzip
import traceback
from datetime import datetime
from collections import defaultdict

from notion_db import fetch_my_table, update_char_list

DATA_FILE = "data/char_data.json"
DATA_FILE_MIN = "data/char_data_min.json"
ALIAS_FILE = "data/alias.json"
# %%


class Updater:
    def __init__(self, template: dict, template_extra: dict, ver: str) -> None:
        self.data = {}
        self.session = requests.Session()

        for name in template:
            char = template[name].copy()
            if name in template_extra:
                char["ver"] = template_extra[name]["ver"]
                char["id"] = template_extra[name]["id"]
                char["name_en"] = template_extra[name]["name_en"]
                # overwrite id (old chars slightly different from official)
            else:
                char["ver"] = ver
            self.data[name] = char

        with open(ALIAS_FILE, "r", encoding="utf8") as f:
            aliases = json.load(f)

        self.alias_to_name = {}
        # an alias may map to multiple names (e.g. Lyney & Lynette)
        for name, char in self.data.items():
            self.alias_to_name[char["name_zh"]] = name
            self.alias_to_name[char["name_en"]] = name
            if name in aliases:
                for _alias in aliases[name]["alias_zh"]:
                    self.alias_to_name[_alias] = name
                for _alias in aliases[name]["alias_en"]:
                    self.alias_to_name[_alias] = name

        self.quotes_zh = self._load_quotes("zh")
        self.quotes_en = self._load_quotes("en")

    def _load_quotes(self, lang):
        if lang == "zh":
            j = json.load(
                gzip.open("data_raw/chinesesimplified-voiceovers.min.json.gzip", "r")
            )
            return j["data"]["ChineseSimplified"]["voiceovers"]
        elif lang == "en":
            j = json.load(gzip.open("data_raw/english-voiceovers.min.json.gzip", "r"))
            return j["data"]["English"]["voiceovers"]
        else:
            raise ValueError("Invalid language for quotes")

    def _find_quote_targets(self, title, current_key, lang) -> set[str]:
        about_str = ["About ", "关于", "对"]
        # 茜特菈莉 "对神里绫华…"
        splitter = {"en": ":", "zh": "·"}
        target_text = title.split(splitter[lang])[0]
        target_keys = set()
        if not any(title.startswith(s) for s in about_str):
            return target_keys
        for alias in self.alias_to_name:
            if (
                self.alias_to_name[alias] != current_key
                and alias.lower() in target_text.lower()
            ):
                # found target, and is not self
                target_keys.add(self.alias_to_name[alias])
        return target_keys

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

    def _find_char_quotes(self, name_zh, lang="zh") -> list[dict]:
        """
        get lines from *char* to other chars
        """
        name = self.data[name_zh]["name_" + lang]
        k = self.data[name_zh]["name_en"].lower().replace(" ", "")
        lines = []

        quotes_dict = self.quotes_zh if lang == "zh" else self.quotes_en

        for q in quotes_dict[k]["friendLines"]:
            title = q["title"]
            title = title.rstrip(" …")
            target_keys = self._find_quote_targets(title, name_zh, lang)

            if not target_keys:
                continue
            
            title = (
                f"{name} {title[0].lower()}{title[1:]}"  # About Y -> X about Y
                if lang == "en"
                else name + title
            )
            for k in target_keys:
                target_id = self.data[k]["id"]
                target_name = self.data[k]["name_" + lang]
                lines.append(
                    {
                        # 'from_'+lang : name,
                        "target_id": target_id,
                        "target_" + lang: target_name,
                        "title_" + lang: title,
                        "content_" + lang: q["description"],
                    }
                )

        return lines

    def find_quotes(self):
        print("Finding quotes")
        for name_zh in self.data:
            char = self.data[name_zh]
            lines_zh = self._find_char_quotes(name_zh, "zh")
            lines_en = self._find_char_quotes(name_zh, "en")
            lines = self._merge_lines(lines_zh, lines_en)
            char["lines"] = lines

    def print_diff(self, data_prev):
        chars_prev = {char["name_zh"]: char for char in data_prev}
        for name, char in self.data.items():
            n_prev = len(chars_prev[name]["lines"]) if name in chars_prev else 0
            n_now = len(char["lines"])
            if n_now != n_prev:
                print(f"  {name} {char['name_en']} (+{n_now-n_prev}={n_now})")

    def update_remote_table(self, char_names_new: list[str]):
        # WIP
        data_update = []
        keys = [
            "id",
            "name_zh",
            "name_en",
            "img_url",
            "ver",
            "gender",
            "region",
            "rarity",
            "weapon",
            "element",
            "height",
        ]
        for name in char_names_new:
            char_info = self.session.get(
                f"https://genshin-db-api.vercel.app/api/v5/characters?query={name}&queryLanguages=ChineseSimplified&resultLanguage=ChineseSimplified"
            ).json()
            char = {}
            for k in keys:
                if k in self.data[name]:
                    char[k] = self.data[name][k]
                elif k in char_info:
                    char[k] = char_info[k]
                elif k == "weapon":
                    char[k] = char_info["weaponText"][0]
                elif k == "element":
                    char[k] = char_info["elementText"]
                elif k == "height":
                    h = 1
                    if char_info["bodyType"].split("_")[1] in ["BOY", "GIRL"]:
                        h = 2
                    if char_info["bodyType"].split("_")[1] in ["MALE", "LADY"]:
                        h = 3
                    char[k] = h
            char["gender"] = "♀️" if char["gender"] == "女" else "♂️"
            data_update.append(char)
        update_char_list(data_update)
        print(f"Added {len(data_update)} chars to notion")

    def write_data_file(self):
        char_data = list(self.data.values())
        char_data.sort(key=lambda x: x["id"])
        with open(DATA_FILE, "w", encoding="utf8") as f:
            json.dump(char_data, f, ensure_ascii=False, indent=4)
        with open(DATA_FILE_MIN, "w", encoding="utf8") as f:
            json.dump(char_data, f, ensure_ascii=False, separators=(",", ":"))
        print("Wrote data files")


def fetch_char_api() -> dict[str, dict[str, str]]:
    S = requests.Session()

    data_zh = S.get(url=os.getenv("URL_ZH"), timeout=20).json()
    data_en = S.get(url=os.getenv("URL_EN"), timeout=20).json()
    char_list_zh = data_zh["data"]["list"]
    char_list_en = data_en["data"]["list"]
    char_count = data_zh["data"]["iTotal"]
    char_dict = {}
    for i, entry in enumerate(char_list_zh):
        name = entry["sTitle"]
        d = {
            "id": char_count - i,  # last one = 1
            "name_zh": name,
            "name_en": char_list_en[i]["sTitle"],
        }
        # order may be slightly different, but remote data should fix it
        img_url = None
        for entry in json.loads(entry["sExt"]).values():
            # entry is a list of dicts
            for entry_item in entry:
                if (
                    img_url is None
                    and "name" in entry_item
                    and (
                        entry_item["name"].startswith("UI_AvatarIcon_")
                        or entry_item["name"].endswith(f"{name}.png")
                        or entry_item["name"].endswith("头像.png")
                        or entry_item["name"].endswith("Icon.png")
                    )
                ):
                    img_url = entry_item["url"]
        if img_url is None:
            raise ValueError(f"Image url missing for {name}")
        d["img_url"] = img_url
        char_dict[name] = d
    return char_dict


def download_quotes():
    # download file from url
    url_prefix = "https://github.com/theBowja/genshin-db-dist/raw/main/data/gzips/"
    files = [
        "english-voiceovers.min.json.gzip",
        "chinesesimplified-voiceovers.min.json.gzip",
    ]
    os.makedirs("data_raw", exist_ok=True)
    print("Downloading quotes")
    for fn in files:
        file_path = f"data_raw/{fn}"
        if (
            os.path.exists(file_path)
            and (
                datetime.now() - datetime.fromtimestamp(os.path.getmtime(file_path))
            ).days
            < 1
        ):
            print(f"  {fn} downloaded today")
        else:
            print(f"  {fn}")
            url = url_prefix + fn
            r = requests.get(url)
            with open(f"data_raw/{fn}", "wb") as f:
                f.write(r.content)


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
    # load aliases
    with open(DATA_FILE, "r", encoding="utf8") as f:
        data_prev = json.load(f)

    ver = calc_ver()

    print(f"Updating for v{ver}")
    print("Fetching mhy api")
    official_dict = fetch_char_api()

    # got current chars, building from it
    char_names = list(official_dict.keys())
    count_total = len(official_dict)
    print(f"  Last3 {' '.join(char_names[:3])}")

    count_old = len(data_prev)
    if count_total <= count_old:
        print(f"  {count_total} released / {count_old} saved")
        print("Already up to date")
        return

    char_names_new = char_names[: count_total - count_old]
    print(f"  New char {' '.join(char_names_new)}")

    download_quotes()

    print("Fetching notion table")
    my_table = fetch_my_table()

    updater = Updater(official_dict, my_table, ver)

    updater.find_quotes()
    updater.print_diff(data_prev)
    updater.update_remote_table(char_names_new)
    updater.write_data_file()

    commit_msg = f"v{ver} {' '.join([char['name_zh']+char['name_en'] for char in updater.data.values() if char['ver']==ver])}"

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


# %%
if __name__ == "__main__":
    main()
