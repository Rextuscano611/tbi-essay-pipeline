import gspread
from google.oauth2.service_account import Credentials
from config import CREDENTIALS_FILE, GOOGLE_SHEET_NAME, SHEET_HEADERS

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_sheet():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open(GOOGLE_SHEET_NAME).sheet1
    return sheet

def init_sheet(sheet):
    """Add headers if sheet is empty."""
    existing = sheet.row_values(1)
    if not existing:
        sheet.append_row(SHEET_HEADERS)
        print("[SHEETS] Headers added.")

def get_existing_ids(sheet):
    """Get all Essay IDs already in sheet to avoid duplicates."""
    try:
        col = sheet.col_values(1)  # Essay ID is column 1
        return set(col[1:])        # Skip header
    except:
        return set()

def write_results(results):
    """Write all processed essays to Google Sheets."""
    print("[SHEETS] Connecting to Google Sheets...")
    sheet = get_sheet()
    init_sheet(sheet)
    existing_ids = get_existing_ids(sheet)

    new_count = 0
    for r in results:
        essay_id = r.get("essay_id", "")
        if essay_id in existing_ids:
            print(f"[SHEETS] Already in sheet, skipping: {essay_id}")
            continue

        row = [
            essay_id,
            r.get("year", ""),
            r.get("filename", ""),
            r.get("detected_language", ""),
            r.get("original_text", ""),
            r.get("english_translation", ""),
            r.get("source_url", ""),
            "done"
        ]
        sheet.append_row(row)
        print(f"[SHEETS] Written: {essay_id}")
        new_count += 1

    print(f"\n[SHEETS] Done. {new_count} new essays written to sheet.")