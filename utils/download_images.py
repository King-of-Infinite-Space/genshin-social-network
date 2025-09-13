import json
import os
import requests


def download_images(char_data_path="data/char_data.json", image_dir="data/image"):
    char_data = json.load(open(char_data_path, encoding="utf-8"))
    os.makedirs(image_dir, exist_ok=True)
    for char in char_data:
        url = char["img_url"]
        name = char["name_zh"]
        ext = url.split(".")[-1]
        filepath = os.path.join(image_dir, f"{name}.{ext}")
        if not os.path.exists(filepath):
            print(f"Downloading {filepath} from {url}")
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                response = requests.get(url, headers=headers, stream=True, timeout=10)
                response.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            except requests.exceptions.RequestException as e:
                print(f"Error downloading {url}: {e}")


if __name__ == "__main__":
    download_images()
