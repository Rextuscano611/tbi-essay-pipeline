import asyncio
import json
import os
from playwright.async_api import async_playwright
from config import BASE_URL, LOGS_DIR

# All years visible in the dropdown
YEARS = [
    "2023-24", "2021-22", "2020-21", "2019-20", "2018-19",
    "2017-18", "2016-17", "2015-16", "2014-15", "2013-14",
    "2012-13", "2011-12", "2010-11", "2009-10", "2008-09",
    "2007-08", "2006-07"
]

async def scrape_year(page, year):
    """Select a year from dropdown and scrape all essay URLs."""
    print(f"\n[SCRAPER] Processing year: {year}")
    essay_links = []

    try:
        # Look for the dropdown and click it
        # Try multiple possible selectors
        dropdown_selectors = [
            "select",
            "[class*='dropdown']",
            "[class*='select']",
            "[class*='year']",
            "button:has-text('Select')",
            "div:has-text('Select A Year')"
        ]

        dropdown_found = False
        for selector in dropdown_selectors:
            try:
                el = await page.query_selector(selector)
                if el:
                    tag = await el.evaluate("el => el.tagName.toLowerCase()")
                    if tag == "select":
                        # Native select element - use select_option
                        await el.select_option(label=year)
                        dropdown_found = True
                        print(f"[SCRAPER] Selected year via <select>: {year}")
                        break
                    else:
                        # Custom dropdown - click to open
                        await el.click()
                        await page.wait_for_timeout(1000)
                        # Try to click the year option
                        option = await page.query_selector(f"text={year}")
                        if option:
                            await option.click()
                            dropdown_found = True
                            print(f"[SCRAPER] Selected year via custom dropdown: {year}")
                            break
            except:
                continue

        if not dropdown_found:
            # Try clicking bottom dropdown (second one visible in screenshot)
            try:
                dropdowns = await page.query_selector_all("select, [role='combobox'], [role='listbox']")
                for dd in dropdowns:
                    try:
                        await dd.select_option(label=year)
                        dropdown_found = True
                        print(f"[SCRAPER] Selected year via fallback dropdown: {year}")
                        break
                    except:
                        continue
            except:
                pass

        if not dropdown_found:
            print(f"[SCRAPER] Could not select year {year} - skipping")
            return []

        # Wait for page to load new content
        await page.wait_for_timeout(3000)

        # Collect all PDF/image links
        links = await page.eval_on_selector_all(
            "a[href], img[src]",
            """elements => elements.map(el => ({
                tag: el.tagName,
                href: el.href || '',
                src: el.src || '',
            }))"""
        )

        skip_keywords = [
            "1682", "1683", "1684",
            "prize", "award", "ceremony", "photo", "gallery",
            "banner", "logo", "icon", "thumb", "avatar",
            "Achievements_Banner", "award.dd2ee"
        ]

        for link in links:
            url = link.get("href") or link.get("src", "")
            if not url:
                continue
            if any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png", ".pdf", ".webp"]):
                filename = url.split("/")[-1].split("?")[0]
                if any(kw in url for kw in skip_keywords):
                    continue
                if any(kw in filename.lower() for kw in skip_keywords):
                    continue
                # Skip next.js image optimization wrappers
                if "_next" in url or "image?url" in url:
                    continue

                essay_links.append({
                    "year": year,
                    "url": url,
                    "filename": filename
                })

        print(f"[SCRAPER] Found {len(essay_links)} essays for {year}")

    except Exception as e:
        print(f"[SCRAPER] Error processing year {year}: {e}")

    return essay_links


async def scrape_all_years():
    """Scrape essay URLs for all years."""
    print("[SCRAPER] Starting browser...")
    all_links = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"[SCRAPER] Loading {BASE_URL}")
        await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)

        # Save page HTML for debugging
        html = await page.content()
        with open(f"{LOGS_DIR}/page_dump.html", "w", encoding="utf-8") as f:
            f.write(html)

        # First scrape current page (2024-25 / latest year)
        print("[SCRAPER] Scraping default/current year first...")
        links = await page.eval_on_selector_all(
            "a[href], img[src]",
            """elements => elements.map(el => ({
                href: el.href || '',
                src: el.src || '',
            }))"""
        )

        skip_keywords = [
            "1682", "1683", "1684", "prize", "award", "ceremony",
            "photo", "gallery", "banner", "logo", "icon", "thumb",
            "Achievements_Banner", "award.dd2ee"
        ]

        for link in links:
            url = link.get("href") or link.get("src", "")
            if not url:
                continue
            if "_next" in url or "image?url" in url:
                continue
            if any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png", ".pdf", ".webp"]):
                filename = url.split("/")[-1].split("?")[0]
                if any(kw in url for kw in skip_keywords):
                    continue
                all_links.append({
                    "year": "2024-25",
                    "url": url,
                    "filename": filename
                })

        print(f"[SCRAPER] Default year: {len(all_links)} essays")

        # Now loop through each year in dropdown
        for year in YEARS:
            year_links = await scrape_year(page, year)
            all_links.extend(year_links)
            # Small delay between years
            await page.wait_for_timeout(2000)

        await browser.close()

    # Remove duplicates by URL
    seen = set()
    unique_links = []
    for item in all_links:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique_links.append(item)

    # Save to logs
    output_path = f"{LOGS_DIR}/scraped_urls.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique_links, f, indent=2, ensure_ascii=False)

    print(f"\n[SCRAPER] TOTAL: {len(unique_links)} unique essays across all years")
    print(f"[SCRAPER] Saved to {output_path}")

    # Print summary by year
    year_counts = {}
    for item in unique_links:
        y = item["year"]
        year_counts[y] = year_counts.get(y, 0) + 1
    print("\n[SCRAPER] Summary by year:")
    for y, count in sorted(year_counts.items()):
        print(f"  {y}: {count} essays")

    return unique_links


# Keep old function name for compatibility with main.py
async def scrape_essay_urls():
    return await scrape_all_years()


if __name__ == "__main__":
    asyncio.run(scrape_all_years())