"""
BEE India — EV Public Charging Stations Data Monitor
Watches the link text "EV Public Charging Stations Data till <date>"
and the PDF URL on https://beeindia.gov.in/show_content.php?lang=1&level=2&ls_id=345&lid=67

When BEE uploads new data, both the date in the link text AND the PDF filename
change — this script tracks both and alerts your Google Chat space via webhook.
"""

import os
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────
WEBHOOK_URL = os.environ["GOOGLE_CHAT_WEBHOOK_URL"]
TARGET_URL  = "https://beeindia.gov.in/show_content.php?lang=1&level=2&ls_id=345&lid=67"
STATE_FILE  = Path("state/last_seen.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://beeindia.gov.in/",
}

# ── Scraper ───────────────────────────────────────────────────────────────────

def scrape() -> dict:
    """
    Fetch the BEE E-Mobility page and extract:
      - link_text : full anchor text e.g. "EV Public Charging Stations Data till 26th October 2025 ..."
      - pdf_url   : href of the PDF e.g. ".../EV_PCS_Data_29277.pdf"
      - page_updated : "Last Updated On" text shown at top of page
    """
    resp = requests.get(TARGET_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # ── Find the EV charging stations data link ───────────────────────────────
    ev_link = None
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        if re.search(r"EV Public Charging Stations Data till", text, re.I):
            ev_link = a
            break

    if ev_link is None:
        raise ValueError(
            "Could not find 'EV Public Charging Stations Data till' link on the page. "
            "The page structure may have changed."
        )

    link_text = ev_link.get_text(strip=True)
    pdf_url   = ev_link["href"]
    # Make absolute if relative
    if pdf_url.startswith("/"):
        pdf_url = "https://beeindia.gov.in" + pdf_url

    # ── Also grab the page-level "Last Updated On" stamp ─────────────────────
    page_updated = ""
    for tag in soup.find_all(string=re.compile(r"Last Updated On", re.I)):
        page_updated = tag.strip()
        break

    return {
        "link_text":    link_text,
        "pdf_url":      pdf_url,
        "page_updated": page_updated,
    }


# ── State ─────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ── Google Chat Alert ─────────────────────────────────────────────────────────

def send_alert(current: dict, previous: dict | None, is_first_run: bool):
    now = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    if is_first_run:
        title    = "🔔 BEE EV Charging Monitor started"
        subtitle = "Baseline recorded — you'll be alerted when data is updated"
        lines = [
            "<b>Currently tracking:</b>",
            f"📄 {current['link_text']}",
            "",
            f"<b>PDF:</b> <a href=\"{current['pdf_url']}\">{current['pdf_url'].split('/')[-1]}</a>",
            f"<b>Page stamp:</b> {current['page_updated']}",
            "",
            f"<a href=\"{TARGET_URL}\">Open BEE E-Mobility page ↗</a>",
        ]
    else:
        title    = "🚨 BEE EV Charging Data updated!"
        subtitle = f"New data detected • {now}"
        lines = ["<b>What changed:</b>", ""]

        if current["link_text"] != previous.get("link_text", ""):
            lines.append(f"<b>Link text (old):</b> {previous.get('link_text', '—')}")
            lines.append(f"<b>Link text (new):</b> <b>{current['link_text']}</b>")
            lines.append("")

        if current["pdf_url"] != previous.get("pdf_url", ""):
            old_file = previous.get("pdf_url", "—").split("/")[-1]
            new_file = current["pdf_url"].split("/")[-1]
            lines.append(f"<b>PDF (old):</b> {old_file}")
            lines.append(f"<b>PDF (new):</b> <b>{new_file}</b>")
            lines.append("")

        lines += [
            f"<a href=\"{current['pdf_url']}\">⬇ Download new PDF</a>",
            f"<a href=\"{TARGET_URL}\">Open BEE page ↗</a>",
        ]

    payload = {
        "cards": [{
            "header": {
                "title": title,
                "subtitle": subtitle,
                "imageUrl": "https://beeindia.gov.in/assets/img/new_logo_main.png",
                "imageStyle": "IMAGE"
            },
            "sections": [{
                "widgets": [{"textParagraph": {"text": "\n".join(lines)}}]
            }]
        }]
    }

    r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
    r.raise_for_status()
    print("  Alert sent to Google Chat ✓")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"BEE EV Monitor — {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}")

    current = scrape()
    print(f"  Link text : {current['link_text']}")
    print(f"  PDF URL   : {current['pdf_url']}")
    print(f"  Page stamp: {current['page_updated']}")

    state    = load_state()
    previous = state.get("data")
    now_iso  = datetime.now(timezone.utc).isoformat()

    # ── First run ─────────────────────────────────────────────────────────────
    if not previous:
        print("  First run: saving baseline.")
        send_alert(current, None, is_first_run=True)
        save_state({"data": current, "last_checked": now_iso})
        print("  Done.")
        sys.exit(0)

    # ── Diff ──────────────────────────────────────────────────────────────────
    changed = (
        current["link_text"] != previous.get("link_text") or
        current["pdf_url"]   != previous.get("pdf_url")
    )

    if changed:
        print("  ⚠️  Change detected! Sending alert.")
        send_alert(current, previous, is_first_run=False)
        save_state({"data": current, "last_checked": now_iso})
    else:
        print("  ✅ No change detected.")
        save_state({"data": previous, "last_checked": now_iso})


if __name__ == "__main__":
    main()
