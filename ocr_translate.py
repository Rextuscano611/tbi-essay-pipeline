import os
import json
import time
import sys
from google import genai
from google.genai import types
from config import (
    GEMINI_API_KEY, GEMINI_MODEL, JSON_DIR,
    MAX_RETRIES, RETRY_DELAY, PROGRESS_FILE, REQUEST_DELAY
)

# Fix Windows Unicode printing
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

client = genai.Client(api_key=GEMINI_API_KEY)

PROMPT = """You are processing a scanned handwritten essay from a student essay competition.

This PDF may have multiple pages - treat all pages as ONE complete essay.

Your tasks:
1. Transcribe ALL the handwritten text EXACTLY as written by the student across all pages.
2. IGNORE any printed footer/header text such as company slogans, logos,
   competition branding, copyright notices, or organizer information.
3. Detect the language of the handwritten essay.
4. Translate the full essay into English.

IMPORTANT: Return ONLY a valid JSON object. 
- Do not include any markdown, backticks, or extra text outside the JSON.
- All string values must use double quotes.
- Escape any double quotes inside text with backslash.
- Do not use newlines inside JSON string values - use \\n instead.

Return exactly this structure:
{
  "detected_language": "language name in English",
  "original_text": "full transcribed handwritten text from all pages",
  "english_translation": "full English translation"
}"""


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}


def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2)


def safe_print(msg):
    """Print that handles Unicode safely on Windows."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', errors='replace').decode('ascii'))


def clean_json_response(raw):
    """Try multiple strategies to extract valid JSON from Gemini response."""
    # Strategy 1: Remove markdown fences
    cleaned = raw.replace("```json", "").replace("```", "").strip()

    # Strategy 2: Find the JSON object boundaries
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start != -1 and end > start:
        cleaned = cleaned[start:end]

    # Strategy 3: Try parsing directly
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 4: Try to fix common issues - unescaped newlines in strings
    import re
    # Replace literal newlines inside JSON strings with \n
    def fix_newlines(s):
        result = []
        in_string = False
        i = 0
        while i < len(s):
            c = s[i]
            if c == '"' and (i == 0 or s[i-1] != '\\'):
                in_string = not in_string
                result.append(c)
            elif in_string and c == '\n':
                result.append('\\n')
            elif in_string and c == '\r':
                result.append('\\r')
            else:
                result.append(c)
            i += 1
        return ''.join(result)

    try:
        fixed = fix_newlines(cleaned)
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        raise e


def process_essay(item):
    """Send one essay to Gemini, return transcription + translation."""
    local_path = item.get("local_path")
    essay_id = item.get("essay_id")
    source_url = item.get("url", "")

    if not local_path or not os.path.exists(local_path):
        safe_print(f"[OCR] File not found: {local_path}")
        return None

    ext = os.path.splitext(local_path)[1].lower()

    for attempt in range(MAX_RETRIES):
        try:
            if ext == ".pdf":
                safe_print(f"[OCR] Sending PDF: {essay_id}")
                with open(local_path, "rb") as f:
                    file_bytes = f.read()
                mime = "application/pdf"
            else:
                safe_print(f"[OCR] Sending image: {essay_id}")
                with open(local_path, "rb") as f:
                    file_bytes = f.read()
                mime = "image/jpeg"
                if ext == ".png":
                    mime = "image/png"
                elif ext == ".webp":
                    mime = "image/webp"

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    types.Part.from_bytes(data=file_bytes, mime_type=mime),
                    PROMPT
                ]
            )

            raw = response.text.strip()
            result = clean_json_response(raw)

            lang = result.get("detected_language", "unknown")
            safe_print(f"[OCR] Done - Language: {lang}")

            final = {
                "essay_id": essay_id,
                "year": item.get("year", "unknown"),
                "filename": item.get("filename", ""),
                "source_url": source_url,
                "detected_language": lang,
                "original_text": result.get("original_text", ""),
                "english_translation": result.get("english_translation", "")
            }

            # Save JSON locally
            os.makedirs(JSON_DIR, exist_ok=True)
            json_path = os.path.join(JSON_DIR, f"{essay_id}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(final, f, indent=2, ensure_ascii=False)
            safe_print(f"[OCR] JSON saved: {json_path}")

            return final

        except json.JSONDecodeError as e:
            safe_print(f"[OCR] JSON parse error (attempt {attempt+1}): {e}")
            # Save raw response for debugging
            debug_path = os.path.join(JSON_DIR, f"{essay_id}_raw_attempt{attempt+1}.txt")
            try:
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(raw if 'raw' in locals() else "no response")
                safe_print(f"[OCR] Raw response saved to: {debug_path}")
            except:
                pass
            time.sleep(RETRY_DELAY)

        except Exception as e:
            err_str = str(e)
            safe_print(f"[OCR] Error (attempt {attempt+1}): {err_str[:150]}")
            if "429" in err_str:
                safe_print(f"[OCR] Quota hit - waiting 70s...")
                time.sleep(70)
            else:
                time.sleep(RETRY_DELAY)

    safe_print(f"[OCR] FAILED: {essay_id}")
    return None


def process_all_essays(downloaded_items, test_mode=False):
    """Process all downloaded essays."""
    progress = load_progress()
    results = []

    items_to_process = downloaded_items[:5] if test_mode else downloaded_items

    if test_mode:
        safe_print(f"[OCR] TEST MODE - processing first 5 essays only")

    total = len(items_to_process)
    for idx, item in enumerate(items_to_process):
        essay_id = item.get("essay_id", "")

        # Skip already processed
        if progress.get(essay_id, {}).get("processed"):
            safe_print(f"[OCR] Already done, skipping: {essay_id}")
            json_path = os.path.join(JSON_DIR, f"{essay_id}.json")
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    results.append(json.load(f))
            continue

        safe_print(f"\n[OCR] -- Essay {idx+1}/{total}: {essay_id}")
        result = process_essay(item)

        if result:
            results.append(result)
            progress[essay_id] = {"downloaded": True, "processed": True}
            save_progress(progress)
            safe_print(f"[OCR] Progress saved.")
        else:
            progress[essay_id] = {"downloaded": True, "processed": False}
            save_progress(progress)

        safe_print(f"[OCR] Waiting {REQUEST_DELAY}s before next request...")
        time.sleep(REQUEST_DELAY)

    safe_print(f"\n[OCR] Done. Processed {len(results)} essays.")
    return results