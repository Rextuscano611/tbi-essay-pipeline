# TBI Essay Translation Pipeline

An automated end-to-end pipeline to scrape, OCR, and translate handwritten student essays from the [Tata Building India](https://www.tatabuildingindia.com/achievements) competition website into English, saving results to Google Sheets.

---

## What It Does

- Scrapes 600+ handwritten essay PDFs/images from the TBI website (year-wise, 2006–2025)
- Uses **Google Gemini 2.5 Flash** (multimodal AI) to:
  - Read handwriting across 8–10 Indian languages (Marathi, Malayalam, Tamil, Gujarati, Urdu, Hindi, Bengali, Telugu, Kannada, etc.)
  - Translate each essay to English
  - Ignore printed footer/branding text automatically
- Saves results to **Google Sheets** with original text + English translation
- Saves every result locally as JSON for backup
- Fully resumable — if quota hits or script crashes, it picks up exactly where it left off

---

## Pipeline Architecture

```
Website (JS-rendered, year-wise dropdown)
        ↓  Playwright (headless Chrome)
scraped_urls.json  →  636 essay URLs across 17 years
        ↓  requests
data/raw/<year>/   →  Downloaded PDFs and images
        ↓  Gemini 2.5 Flash API (1 request per essay)
data/json/         →  {language, original_text, english_translation}
        ↓  Google Sheets API
essay_sheet        →  Master spreadsheet with all essays
```

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.12 | Core language |
| Playwright | Scraping JS-rendered website |
| Google Gemini 2.5 Flash | Handwriting OCR + Translation |
| gspread + google-auth | Google Sheets integration |
| Pillow | Image processing |
| pdf2image | PDF handling |

---

## Project Structure

```
tbi-essay-pipeline/
├── main.py              # Runs full pipeline (Steps 1-4)
├── scraper.py           # Playwright scraper - all years
├── scrape_only.py       # Run scrape + download only
├── downloader.py        # Downloads essay files
├── ocr_translate.py     # Gemini OCR + translation
├── sheets_writer.py     # Writes to Google Sheets
├── config.py            # All settings
├── requirements.txt     # Python dependencies
├── .env                 # API keys (not committed)
├── credentials.json     # Google service account (not committed)
└── data/                # Downloaded essays + outputs (not committed)
    ├── raw/             # Downloaded PDFs/images by year
    ├── json/            # Per-essay JSON results
    └── logs/            # Progress tracking + scrape logs
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/Rextuscano611/tbi-essay-pipeline.git
cd tbi-essay-pipeline
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
playwright install chromium
```

### 2. Get Gemini API Key
- Go to [aistudio.google.com](https://aistudio.google.com)
- Click **Get API Key** → Create API Key (free)

### 3. Get Google Sheets Credentials
- Go to [Google Cloud Console](https://console.cloud.google.com)
- Create a project → Enable **Google Sheets API** + **Google Drive API**
- Create a **Service Account** → Download key as `credentials.json`
- Share your Google Sheet with the service account email (Editor access)

### 4. Configure `.env`

```env
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_SHEET_NAME=essay_sheet
```

### 5. Run

```bash
# Full pipeline (scrape + download + OCR + translate + sheets)
python main.py

# Scrape and download only
python scrape_only.py
```

---

## Output — Google Sheets

| Essay ID | Year | Filename | Detected Language | Original Text | English Translation | Source URL | Status |
|----------|------|----------|-------------------|---------------|--------------------|----|--------|
| 2024-25_TBI009332Senior.pdf | 2024-25 | TBI009332Senior.pdf | Marathi | हमारा देश... | Our country... | url | done |

---

## Key Features

- **Resume support** — tracks progress in `data/logs/progress.json`, never re-processes completed essays
- **Rate limit handling** — automatically waits and retries on quota errors
- **Smart filtering** — skips prize ceremony photos, banners, and logos
- **Robust JSON parsing** — 4 fallback strategies to handle Gemini response variations
- **Windows Unicode safe** — handles Indian language characters on Windows terminals

---

## Quota & Cost

| Plan | Daily limit | Cost for 636 essays |
|------|------------|-------------------|
| Free tier | 20 req/day | ₹0 (32 days) |
| Pay-as-you-go | 1,500 req/day | ~₹200 (1 night) |

---

## Built By

Rex — AI/ML Intern   
Part of NLP + document processing project.
