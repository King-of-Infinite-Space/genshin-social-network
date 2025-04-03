import os
import requests
from notion_client import Client

notion = Client(auth=os.environ["NOTION_GENSHIN"], timeout_ms=10000)
database_id = "482ae398eca5496aaa0b28c87bc8ba70"


def getProp(page: dict, prop: str):
    prop = page["properties"][prop]
    propType = prop["type"]
    if propType in ["rich_text", "title"]:
        content = prop[propType]
        value = content[0]["plain_text"] if len(content) else ""
    elif propType == "select":
        value = prop[propType]["name"]
    else:
        value = prop[propType]
    return value


def fillProps(data: dict, schema: dict):
    d = {}
    for k in data:
        if data[k] is not None and data[k] != "":
            dtype = schema[k]["type"]
            if dtype in ["rich_text", "title"]:
                d[k] = {dtype: [{"text": {"content": data[k]}}]}
            elif dtype == "select":
                for option in schema[k]["select"]["options"]:
                    if option["name"] == str(data[k]):
                        d[k] = {"select": {"id": option["id"]}}
                        break
            else:
                d[k] = {dtype: data[k]}
    return d


def fetch_my_table():
    response = notion.databases.query(
        database_id,
        sorts=[
            {
                "property": "id",
                "direction": "descending",
            }
        ],
    )
    pages = response["results"]
    chars = {}
    for page in pages:
        char = {}
        for prop in [
            "id",
            "name_zh",
            "name_en",
            "url_name",
            "ver",
        ]:
            char[prop] = getProp(page, prop)
        chars[char["name_zh"]] = char
    return chars

def update_remote_table(char_dict: dict, new_names: list[str]):
    update_list = []
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
    for name in new_names:
        try:
            char_info = requests.get(
                f"https://genshin-db-api.vercel.app/api/v5/characters?query={name}&queryLanguages=ChineseSimplified&resultLanguage=ChineseSimplified"
            ).json()
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            continue
        entry = {}
        for k in keys:
            if k in char_dict[name]:
                entry[k] = char_dict[name][k]
            elif k in char_info:
                entry[k] = char_info[k]
            elif k == "weapon":
                entry[k] = char_info["weaponText"][0]
            elif k == "element":
                entry[k] = char_info["elementText"]
            elif k == "height":
                h = 1
                if char_info["bodyType"].split("_")[1] in ["BOY", "GIRL"]:
                    h = 2
                if char_info["bodyType"].split("_")[1] in ["MALE", "LADY"]:
                    h = 3
                entry[k] = h
        entry["gender"] = "♀️" if entry["gender"] == "女" else "♂️"
        update_list.append(entry)

    schema = notion.databases.retrieve(database_id)["properties"]

    added_count = 0
    for entry in update_list:
        # Check if entry with same name already exists
        filter = {"property": "name_zh", "rich_text": {"equals": entry["name_zh"]}}
        q = notion.databases.query(database_id, filter=filter)
        
        # Only add if there are no existing entries with this name
        if len(q["results"]) == 0:
            notion.pages.create(
                parent={"database_id": database_id}, properties=fillProps(entry, schema)
            )
            added_count += 1
    
    print(f"Added {added_count} / {len(new_names)} chars to notion")