import asyncio
import json
import os
from config import LOGS_DIR, RAW_DIR, JSON_DIR
from scraper import scrape_essay_urls
from downloader import download_essays
from ocr_translate import process_all_essays
from sheets_writer import write_results

def ensure_dirs():
    for d in [RAW_DIR, JSON_DIR, LOGS_DIR]:
        os.makedirs(d, exist_ok=True)

async def main():
    ensure_dirs()
    print("=" * 50)
    print("  ESSAY PIPELINE - TATA BUILDING INDIA")
    print("=" * 50)

    # STEP 1: Scrape
    print("\n[STEP 1] Scraping essay URLs...")
    essay_links = await scrape_essay_urls()

    if not essay_links:
        print("[ERROR] No essays found. Check logs/page_dump.html to inspect the page.")
        return

    # STEP 2: Download
    print(f"\n[STEP 2] Downloading {len(essay_links)} essays...")
    downloaded = download_essays(essay_links)

    # STEP 3: OCR + Translate
    print(f"\n[STEP 3] OCR + Translation via Gemini...")
    results = process_all_essays(downloaded, test_mode=True)
    

    # STEP 4: Write to Google Sheets
    print(f"\n[STEP 4] Writing {len(results)} results to Google Sheets...")
    write_results(results)

    print("\n" + "=" * 50)
    print(f"  PIPELINE COMPLETE - {len(results)} essays processed")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())