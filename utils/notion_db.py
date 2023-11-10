from socket import timeout
import os
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


def update_char_list(update_list):
    schema = notion.databases.retrieve(database_id)["properties"]

    gender_dict = {"女": "♀️", "男": "♂️"}
    weapon_dict = {
        "sword": "单",
        "claymore": "双",
        "polearm": "长",
        "bow": "弓",
        "catalyst": "法",
    }
    element_dict = {
        "anemo": "风",
        "geo": "岩",
        "electro": "雷",
        "hydro": "水",
        "pyro": "火",
        "cryo": "冰",
        "dendro": "草",
    }
    for char in update_list:
        # char["gender"] = gender_dict[char["gender"]]
        char["weapon"] = weapon_dict[char["weapon"]]
        char["element"] = element_dict[char["element"]]
        char["rarity"] = int(char["rarity"])
        filter = {"property": "name_zh", "rich_text": {"equals": char["name_zh"]}}
        q = notion.databases.query(database_id, filter=filter)
        if len(q["results"]):
            raise Exception("Character already exists in remote table")
        else:
            notion.pages.create(
                parent={"database_id": database_id}, properties=fillProps(char, schema)
            )
