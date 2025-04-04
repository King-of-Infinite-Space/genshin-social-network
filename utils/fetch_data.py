# %%
import requests
import json
import subprocess
import os
import traceback
from datetime import datetime

from prepare_data import download_data, prepare_data
from notion_db import update_remote_table

DATA_FILE = "data/char_data.json"
DATA_FILE_MIN = "data/char_data_min.json"
ALIAS_FILE = "data/alias.json"
# %%


def make_graph(edge_data, node_data):
    """
    process edges to get lines between chars
    """
    name_to_avatarID = {entry["name_zh"]: entry["avatarId"] for entry in node_data}
    avatarID_to_nameZH = {entry["avatarId"]: entry["name_zh"] for entry in node_data}
    avatarID_to_nameEN = {entry["avatarId"]: entry["name_en"] for entry in node_data}
    target_to_avatarID = {}  # target can be name or alias

    aliases = json.load(open(ALIAS_FILE, encoding="utf8"))
    for char in node_data:
        target_to_avatarID[char["name_zh"]] = char["avatarId"]
        target_to_avatarID[char["name_en"]] = char["avatarId"]
        name = char["name_zh"]
        if name in aliases:
            for _alias in aliases[name]["alias_zh"] + aliases[name]["alias_en"]:
                target_to_avatarID[_alias] = name_to_avatarID[name]

    def process_title(title, prefix="", remove_about=False, strip=False) -> str:
        if strip:
            title = title.rstrip("…")
        about_str = ["About ", "关于", "对"]
        # 茜特菈莉 "对神里绫华…"
        if remove_about:
            for s in about_str:
                title = title.removeprefix(s)
        return prefix + title

    def process_content(content) -> str:
        # fix line break
        content = content.replace("\\n", "\n")
        return content

    def find_quote_targets(title, curr_avatarID, lang) -> set[str]:
        splitter = {"en": ":", "zh": "·"}
        target_text = title.split(splitter[lang])[0]
        target_avatarIds = set()
        if process_title(title, remove_about=True) == title:
            return target_avatarIds
        for target in target_to_avatarID:
            if (
                target_to_avatarID[target] != curr_avatarID
                and target.lower() in target_text.lower()
            ):
                # found target, and is not self
                target_avatarIds.add(target_to_avatarID[target])
        return target_avatarIds

    char_dict = {entry["name_zh"]: entry | {"lines": []} for entry in node_data}

    for edge in edge_data:
        targets = set()
        for lang in ["zh", "en"]:
            targets |= find_quote_targets(edge["title_" + lang], edge["avatarId"], lang)
        if not targets:
            continue
        source_id = edge["avatarId"]
        for target_id in targets:
            line = {
                "target_zh": avatarID_to_nameZH[target_id],
                "title_zh": process_title(
                    edge["title_zh"],
                    prefix=avatarID_to_nameZH[source_id],
                    strip=True
                ),
                "content_zh": process_content(edge["content_zh"]),
                "target_en": avatarID_to_nameEN[target_id],
                "title_en": process_title(
                    edge["title_en"],
                    prefix=avatarID_to_nameEN[source_id] + " about",
                    remove_about=True, strip=True
                ),
                "content_en": process_content(edge["content_en"]),
            }
            char_dict[avatarID_to_nameZH[source_id]]["lines"].append(line)

    return char_dict


def merge_data(char_dict: dict, offical_dict: dict, prev_dict: dict, ver: str):
    char_dict_new = {}
    for name in offical_dict:
        char = {}
        char["id"] = prev_dict.get(name, offical_dict[name])["id"]
        char["name_zh"] = char_dict[name]["name_zh"]
        char["name_en"] = char_dict[name]["name_en"]
        char["img_url"] = offical_dict[name]["img_url"]
        char["ver"] = prev_dict.get(name, {"ver": ver})["ver"]
        char["lines"] = char_dict[name]["lines"]
        char_dict_new[name] = char
    return char_dict_new


def print_diff(char_dict, prev_dict):
    print("New lines")
    for name, char in char_dict.items():
        n_prev = len(prev_dict[name]["lines"]) if name in prev_dict else 0
        n_now = len(char["lines"])
        if n_now != n_prev:
            print(f"  {name} {char['name_en']} (+{n_now - n_prev}={n_now})")


def write_data_file(char_dict: dict):
    char_data = list(char_dict.values())
    char_data.sort(key=lambda x: x["id"])
    with open(DATA_FILE, "w", encoding="utf8") as f:
        json.dump(char_data, f, ensure_ascii=False, indent=4)
    with open(DATA_FILE_MIN, "w", encoding="utf8") as f:
        json.dump(char_data, f, ensure_ascii=False, separators=(",", ":"))
    print("Wrote data files")


def fetch_char_official() -> dict[str, dict[str, str]]:
    S = requests.Session()

    data_zh = S.get(url=os.getenv("URL_ZH"), timeout=20).json()
    char_list_zh = data_zh["data"]["list"]
    char_count = data_zh["data"]["iTotal"]
    char_dict = {}
    for i, entry in enumerate(char_list_zh):
        name = entry["sTitle"]
        d = {
            "id": char_count - i,  # last one = 1
            "name_zh": name,
        }
        # I assigned different id for older chars
        # fix it later with previous data (or remote table)
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


def calc_ver():
    ref_ver = os.environ["REF_VER"]
    if ref_ver is None:
        return ""
    ref_date = os.environ["REF_DATE"]
    period = os.environ["PERIOD"]
    offset = os.getenv("VER_ADJUST", "0.0")
    n_offset = int(100 * float(offset))
    dd = (datetime.now() - datetime.fromisoformat(ref_date)).days
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


def find_new_chars(official_dict, data_prev):
    """
    get new chars from official dict
    """
    char_names = list(official_dict.keys())
    count_total = len(official_dict)
    count_old = len(data_prev)
    if count_total <= count_old:
        return []
    char_names_new = char_names[: count_total - count_old]
    return char_names_new


def main():
    with open(DATA_FILE, "r", encoding="utf8") as f:
        data_prev = json.load(f)
    prev_dict = {char["name_zh"]: char for char in data_prev}

    ver = calc_ver()
    print(f"Updating for v{ver}")

    print("Fetching mhy api")
    official_dict = fetch_char_official()

    new_names = find_new_chars(official_dict, prev_dict)
    if not new_names:
        print("No new chars found")
        return
    print(f"  New char {' '.join(new_names)}")

    download_data()
    node_data, edge_data = prepare_data()
    char_dict = make_graph(edge_data, node_data)

    char_dict = merge_data(char_dict, official_dict, prev_dict, ver)

    print_diff(char_dict, prev_dict)
    write_data_file(char_dict)

    update_remote_table(char_dict, new_names)

    commit_msg = f"v{ver} {' '.join([char['name_zh'] + char['name_en'] for char in char_dict.values() if char['ver'] == ver])}"

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
