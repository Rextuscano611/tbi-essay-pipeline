import os
import json
import requests
import time
from config import RAW_DIR, LOGS_DIR, PROGRESS_FILE

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)

def download_essays(essay_links):
    """
    Downloads all essay images/PDFs, organized by year.
    Skips already downloaded files.
    """
    progress = load_progress()
    downloaded = []

    for idx, item in enumerate(essay_links):
        url = item["url"]
        year = item["year"]
        filename = item["filename"]

        # Create year folder
        year_dir = os.path.join(RAW_DIR, year)
        os.makedirs(year_dir, exist_ok=True)

        save_path = os.path.join(year_dir, filename)
        essay_id = f"{year}_{filename}"

        # Skip if already downloaded
        if os.path.exists(save_path):
            print(f"[DOWNLOADER] Skipping (exists): {essay_id}")
            item["local_path"] = save_path
            item["essay_id"] = essay_id
            downloaded.append(item)
            continue

        try:
            print(f"[DOWNLOADER] Downloading ({idx+1}/{len(essay_links)}): {filename}")
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            with open(save_path, "wb") as f:
                f.write(response.content)

            item["local_path"] = save_path
            item["essay_id"] = essay_id
            downloaded.append(item)

            # Update progress
            progress[essay_id] = {"downloaded": True, "processed": False}
            save_progress(progress)

            time.sleep(0.5)  # be polite to server

        except Exception as e:
            print(f"[DOWNLOADER] Failed: {filename} — {e}")
            item["local_path"] = None
            item["essay_id"] = essay_id

    print(f"\n[DOWNLOADER] Done. {len(downloaded)} files ready.")
    return downloaded


if __name__ == "__main__":
    with open(f"{LOGS_DIR}/scraped_urls.json", "r") as f:
        links = json.load(f)
    download_essays(links)