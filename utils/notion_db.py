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
    weapon_map = {
        "WEAPON_SWORD_ONE_HAND": "单手剑",
        "WEAPON_CLAYMORE": "双手剑",
        "WEAPON_POLE": "长柄武器",
        "WEAPON_BOW": "弓",
        "WEAPON_CATALYST": "法器"
    }
    height_map = {
        "BODY_LOLI": 1,
        "BODY_BOY": 2,
        "BODY_GIRL": 2,
        "BODY_MALE": 3,
        "BODY_LADY": 3,
    }
    gender_map = {
        "BODY_LOLI": "♀️",
        "BODY_GIRL": "♀️",
        "BODY_LADY": "♀️",
    }
    region_map = {
        "MONDSTADT": "蒙德",
        "LIYUE": "璃月",
        "INAZUMA": "稻妻",
        "SUMERU": "须弥",
        "FONTAINE": "枫丹",
        "NATLAN": "纳塔",
        "FATUI": "至冬",
        "SNEZHNAYA": "至冬", # not exist yet, just a guess
    }
    update_list = []
    for name in new_names:
        char = char_dict[name]
        entry = {k: char.get(k, "") for k in keys}
        entry["weapon"] = weapon_map.get(char["weaponType"], " ")[0]
        entry["height"] = height_map.get(char["bodyType"], 1)
        entry["gender"] = gender_map.get(char["bodyType"], "♂️")
        entry["region"] = region_map.get(char["region"], "坎瑞亚")
        update_list.append(entry)

    schema = notion.databases.retrieve(database_id)["properties"]

    prev_table_dict = fetch_my_table()
    added_count = 0
    for entry in update_list:
        if entry["name_zh"] not in prev_table_dict:
            notion.pages.create(
                parent={"database_id": database_id}, properties=fillProps(entry, schema)
            )
            added_count += 1
    
    print(f"Added {added_count} / {len(new_names)} chars to notion")