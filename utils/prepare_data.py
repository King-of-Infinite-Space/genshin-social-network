import os
import json
import time
import requests

data_path = {
    "node_data": "ExcelBinOutput/AvatarExcelConfigData.json",
    "edge_data": "ExcelBinOutput/FettersExcelConfigData.json",
    "textmap_zh": "TextMap/TextMapCHS.json",
    "textmap_en": "TextMap/TextMapEN.json",
}

def download_file(url, download_path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(download_path, "wb") as f:
            f.write(response.content)
        return True
    return False

def download_data(max_age_hours=24):
    print("Downloading source data")
    os.makedirs("data_raw", exist_ok=True)
    for key, path in data_path.items():
        download_path = os.path.join("data_raw", path.split("/")[-1])
        # Check if file exists and is recent enough
        file_age_hours = float("inf")
        if os.path.exists(download_path):
            file_age_seconds = time.time() - os.path.getmtime(download_path)
            file_age_hours = file_age_seconds / 3600
        if file_age_hours < max_age_hours:
            print(f"\tSkipping {download_path}, file is less than {max_age_hours} hours old")
        else:
            url = f"{os.environ['DATA_REPO_URL']}{path}?inline=false"
            success = download_file(url, download_path)
            if success:
                print(f"\tDownloaded {download_path}")
            else:
                print(f"Failed to download {url}")
            

def prepare_data():
    data_raw = {
        k: json.load(open(os.path.join("data_raw", v.split('/')[-1]), encoding="utf-8"))
        for k, v in data_path.items()
    }
    node_data = []
    for node_raw in data_raw["node_data"]:
        node = {
            "avatarId": node_raw["id"],
            "name_zh": data_raw["textmap_zh"][str(node_raw["nameTextMapHash"])],
            "name_en": data_raw["textmap_en"][str(node_raw["nameTextMapHash"])],
            # "rarity": 5 if node_raw["qualityType"] == "QUALITY_ORANGE" else 4,
            # "bodyType": node_raw["bodyType"],
            # "weaponType": node_raw["weaponType"],
        }
        node_data.append(node)
    edge_data = []
    for edge_raw in data_raw["edge_data"]:
        edge = {
            "avatarId": edge_raw["avatarId"],
            "fetterId": edge_raw["fetterId"],
            "title_zh": data_raw["textmap_zh"][str(edge_raw["voiceTitleTextMapHash"])],
            "title_en": data_raw["textmap_en"][str(edge_raw["voiceTitleTextMapHash"])],
            "content_zh": data_raw["textmap_zh"][str(edge_raw["voiceFileTextTextMapHash"])],
            "content_en": data_raw["textmap_en"][str(edge_raw["voiceFileTextTextMapHash"])],
        }
        edge_data.append(edge)
    return node_data, edge_data