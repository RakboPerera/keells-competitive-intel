# Competitive Intelligence Dashboard
### Keells Super — Sri Lankan Retail Market

AI-powered tool that scrapes Meta Ad Library for competitor campaigns and provides comparative analysis.

**Competitors:** Cargills Food City · Glomark · Spar Sri Lanka  
**Benchmark:** Keells Super

## Features

- 🤖 **Automated Ad Scraping** — Playwright browser extracts ads from Meta Ad Library
- 📣 **Campaign Tracker** — Filter by date range, view creatives, platform breakdown
- ⚔️ **AI Analysis** — Claude compares Keells vs competitors with actionable recommendations
- 🔄 **Daily Auto-Refresh** — GitHub Actions scrapes fresh data every morning

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/keells-competitive-intel.git
cd keells-competitive-intel
pip install -r requirements.txt
playwright install chromium
python ad_scraper.py          # Scrape ads (~3 min)
streamlit run intel_dashboard.py   # Open dashboard
```

## Deploy to Streamlit Cloud

1. Push repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app → select repo
3. Set main file: `intel_dashboard.py`
4. Add secret: `ANTHROPIC_API_KEY = "sk-ant-..."`
5. Deploy → share the URL with your team

## Auto-Refresh (GitHub Actions)

The repo includes a GitHub Actions workflow that scrapes the Ad Library daily at 6 AM Sri Lanka time and commits fresh data. Your colleagues always see up-to-date campaigns.

To enable: Go to repo **Settings → Actions → General → Allow all actions**. The workflow also has a manual trigger button.

## Files

| File | Purpose |
|---|---|
| `intel_dashboard.py` | Streamlit dashboard |
| `ad_scraper.py` | Playwright Ad Library scraper |
| `.github/workflows/scrape.yml` | Daily auto-scrape |
| `data/ad_library_data.json` | Scraped ad data (auto-updated) |

## API Key

Only one key needed: **Claude API** from [console.anthropic.com](https://console.anthropic.com) (~$0.03 per analysis run).

No Meta/Facebook key needed — the scraper uses browser automation.
