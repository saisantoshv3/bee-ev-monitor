# BEE EV Charging Data Monitor → Google Chat Alerts

Monitors the **BEE India E-Mobility page** for changes to:

> *EV Public Charging Stations Data till **26th October 2025** (Click to view the detailed list)*

When BEE uploads new data, both the **date in the link text** and the **PDF filename** change.
This script detects either change and immediately sends a card alert to your Google Chat space.

**Page monitored:** https://beeindia.gov.in/show_content.php?lang=1&level=2&ls_id=345&lid=67  
**Runs on:** GitHub Actions (free, no server)  
**Schedule:** Twice a week (Mon + Thu at 9 AM IST)

---

## Repo Structure

```
your-repo/
├── monitor.py                        ← scraper + alert logic
├── state/
│   └── last_seen.json                ← auto-updated after each run
├── .github/
│   └── workflows/
│       └── monitor.yml               ← GitHub Actions schedule
└── README.md
```

---

## Setup

### 1. Create a Google Chat Webhook
- Open your Google Chat space → click space name → **Apps & Integrations** → **Add webhooks**
- Name it (e.g. "BEE Monitor") and copy the webhook URL

### 2. Push these files to a new GitHub repo

```bash
git init bee-ev-monitor
cd bee-ev-monitor
# copy all 4 files/folders here
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/bee-ev-monitor
git push -u origin main
```

### 3. Add the secret
**Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|------|-------|
| `GOOGLE_CHAT_WEBHOOK_URL` | Your Google Chat webhook URL |

### 4. Run manually to set the baseline
**Actions tab → BEE EV Charging Data Monitor → Run workflow**

This first run records the current link text and PDF URL, then sends a confirmation to Chat:

> 🔔 BEE EV Charging Monitor started
> Currently tracking:
> 📄 EV Public Charging Stations Data till 26th October 2025 (Click to view...)
> PDF: EV_PCS_Data_29277.pdf

---

## What the update alert looks like

> 🚨 BEE EV Charging Data updated!
> New data detected • 01 May 2026, 03:31 UTC
>
> **Link text (old):** EV Public Charging Stations Data till 26th October 2025 …
> **Link text (new):** EV Public Charging Stations Data till 31st March 2026 …
>
> **PDF (old):** EV_PCS_Data_29277.pdf
> **PDF (new):** EV_PCS_Data_31456.pdf
>
> ⬇ Download new PDF | Open BEE page ↗

---

