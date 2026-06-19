import asyncio
from scraper import scrape_essay_urls
from downloader import download_essays

async def main():
    print("Scraping all years...")
    links = await scrape_essay_urls()
    print(f"\nDownloading {len(links)} essays...")
    download_essays(links)
    print("\nDone! All essays downloaded.")

asyncio.run(main())