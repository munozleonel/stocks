# MSP Portfolio Dashboard

A self-hosted stock portfolio tracker with candlestick charts, live prices, currency conversion, and P&L tracking — hosted free on GitHub Pages and auto-updated via GitHub Actions.

## Live URL

After setup: `https://<your-username>.github.io/<repo-name>/`

---

## Setup (one-time, ~5 minutes)

### 1. Create a GitHub repository

```bash
# On GitHub.com → New repository
# Name it e.g. "msp-portfolio"  (can be private ✓)
# Do NOT initialise with a README (you'll push this folder)
```

### 2. Push this project

```bash
cd msp-portfolio
git init
git add .
git commit -m "init: MSP portfolio dashboard"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/msp-portfolio.git
git push -u origin main
```

### 3. Enable GitHub Pages

1. Go to your repo → **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / folder: `/docs`
4. Click **Save**

Your dashboard is now live at `https://YOUR_USERNAME.github.io/msp-portfolio/`

> **Note:** The page will show an error on first load until `data.json` is generated (step 4).

### 4. Trigger the first data fetch

1. Go to your repo → **Actions** tab
2. Click **Update Portfolio Data** → **Run workflow** → **Run workflow**
3. Wait ~60 seconds for it to finish
4. Reload your dashboard — charts should now appear ✓

---

## How it works

```
GitHub Actions (cron)
       │
       ▼
scripts/fetch_data.py        ← downloads OHLC + quotes via yfinance
       │
       ▼
docs/data.json               ← committed back to the repo
       │
       ▼
GitHub Pages serves docs/    ← index.html loads data.json on page open
```

### Update schedule

Runs automatically on weekdays (AEST):
- **6:30 AM** — before ASX opens
- **11:30 PM** — after US markets close

You can also trigger a manual run any time from the **Actions** tab.

---

## Local development

```bash
# Install dependency
pip install yfinance

# Fetch fresh data
python scripts/fetch_data.py

# Serve locally
cd docs
python -m http.server 8080
# Open http://localhost:8080
```

---

## Customising your holdings

Edit the `HOLDINGS` list in **both** files to match your actual portfolio:

- `scripts/fetch_data.py` — controls what data is fetched
- `docs/index.html` — controls what is displayed (shares, avg cost)

Use standard Yahoo Finance ticker symbols:
| Exchange | Format | Example |
|----------|--------|---------|
| US stocks | `TICKER` | `AAPL`, `TSLA` |
| ASX | `TICKER.AX` | `CBA.AX`, `BHP.AX` |
| Paris | `TICKER.PA` | `CAP.PA` |
| Crypto (AUD) | `COIN-AUD` | `BTC-AUD`, `ETH-AUD` |

---

## Files

```
msp-portfolio/
├── .github/
│   └── workflows/
│       └── update-data.yml   ← GitHub Actions schedule
├── scripts/
│   └── fetch_data.py         ← data fetcher (run by Actions)
├── docs/                     ← GitHub Pages root
│   ├── index.html            ← the dashboard
│   └── data.json             ← auto-generated, do not edit manually
├── requirements.txt
└── README.md
```
