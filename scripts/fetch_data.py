#!/usr/bin/env python3
"""
fetch_data.py
Fetches OHLC history + live quotes for every holding using yfinance.
Writes docs/data.json  — consumed by the portfolio dashboard.
Run locally:  python scripts/fetch_data.py
Run via CI:   called by GitHub Actions on a schedule.
"""

import json, datetime, sys, os, time
import yfinance as yf

# ── Holdings ──────────────────────────────────────────────────────────────────
HOLDINGS = [
    {"sym": "AAPL",    "name": "Apple Inc.",                   "shares": 4,       "avgCost": 240.0000, "currency": "USD"},
    {"sym": "AMZN",    "name": "Amazon.com, Inc.",             "shares": 8.9087,  "avgCost": 2245.000, "currency": "USD"},
    {"sym": "META",    "name": "Meta Platforms, Inc.",         "shares": 15.0007, "avgCost": 189.5068, "currency": "USD"},
    {"sym": "TSLA",    "name": "Tesla, Inc.",                  "shares": 83.7728, "avgCost": 242.4156, "currency": "USD"},
    {"sym": "BABA",    "name": "Alibaba Group Holding",        "shares": 23.0000, "avgCost": 166.4426, "currency": "USD"},
    {"sym": "COIN",    "name": "Coinbase Global, Inc.",        "shares": 9.0000,  "avgCost": 166.2911, "currency": "USD"},
    {"sym": "BA",      "name": "Boeing Company (The)",         "shares": 6.0000,  "avgCost": 174.4433, "currency": "USD"},
    {"sym": "CQQQ",    "name": "Invesco China Technology ETF", "shares": 20.0000, "avgCost": 66.7000,  "currency": "USD"},
    {"sym": "CRSR",    "name": "Corsair Gaming, Inc.",         "shares": 36.9300, "avgCost": 36.0049,  "currency": "USD"},
    {"sym": "MU",      "name": "Micron Technology, Inc.",      "shares": 5.0000,  "avgCost": 59.3700,  "currency": "USD"},
    {"sym": "NFLX",    "name": "Netflix, Inc.",                "shares": 20.0000, "avgCost": 382.0000, "currency": "USD"},
    {"sym": "UNH",     "name": "UnitedHealth Group",           "shares": 4.0000,  "avgCost": 230.9125, "currency": "USD"},
    {"sym": "V",       "name": "Visa Inc.",                    "shares": 3.0000,  "avgCost": 209.2633, "currency": "USD"},
    {"sym": "BRK-B",   "name": "Berkshire Hathaway Inc.",      "shares": 2.0000,  "avgCost": 177.1200, "currency": "USD"},
    {"sym": "CAP.PA",  "name": "Capgemini",                    "shares": 27.8578, "avgCost": 90.4557,  "currency": "EUR"},
    {"sym": "A2M.AX",  "name": "A2 Milk Co.",                  "shares": 220.0,   "avgCost": 9.2684,   "currency": "AUD"},
    {"sym": "NCK.AX",  "name": "Nick Scali Ltd.",              "shares": 155.0,   "avgCost": 6.5000,   "currency": "AUD"},
    {"sym": "WBC.AX",  "name": "Westpac Banking Corp.",        "shares": 36.0,    "avgCost": 27.8000,  "currency": "AUD"},
    {"sym": "VAS.AX",  "name": "Vanguard Aust Shares ETF",     "shares": 10.0,    "avgCost": 72.8500,  "currency": "AUD"},
    {"sym": "ETH-AUD", "name": "Ethereum",                     "shares": 1.12,    "avgCost": 1000.0,   "currency": "AUD"},
]

FX_PAIRS = ["AUDUSD=X", "EURUSD=X", "EURAUD=X"]

RANGE_MAP = {
    "7D":  ("7d",  "1d"),
    "3M":  ("3mo", "1d"),
    "12M": ("1y",  "1d"),
}


def fetch_ohlc(sym: str) -> dict:
    """Return {7D: [...], 3M: [...], 12M: [...]} for one symbol."""
    result = {}
    ticker = yf.Ticker(sym)
    for key, (period, interval) in RANGE_MAP.items():
        try:
            df = ticker.history(period=period, interval=interval, auto_adjust=True)
            if df.empty:
                print(f"  [WARN] {sym} {key}: empty dataframe", file=sys.stderr)
                result[key] = []
                continue
            candles = []
            for ts, row in df.iterrows():
                # ts is a pandas Timestamp; convert to ms epoch
                epoch_ms = int(ts.timestamp() * 1000)
                candles.append({
                    "t": epoch_ms,
                    "o": round(float(row["Open"]),  4),
                    "h": round(float(row["High"]),  4),
                    "l": round(float(row["Low"]),   4),
                    "c": round(float(row["Close"]), 4),
                })
            result[key] = candles
            print(f"  {sym:12s} {key:4s}  {len(candles)} candles")
        except Exception as e:
            print(f"  [ERROR] {sym} {key}: {e}", file=sys.stderr)
            result[key] = []
        time.sleep(0.1)   # be polite to Yahoo
    return result


def fetch_quote(sym: str) -> dict:
    """Return {price, prev, currency} for one symbol."""
    try:
        t = yf.Ticker(sym)
        info = t.fast_info
        price = float(info.last_price)
        prev  = float(info.previous_close) if info.previous_close else price
        cur   = getattr(info, "currency", "USD")
        return {"price": round(price, 4), "prev": round(prev, 4), "currency": cur}
    except Exception as e:
        print(f"  [ERROR] quote {sym}: {e}", file=sys.stderr)
        return None


def fetch_fx() -> dict:
    """Return {FROM_TO: rate, ...} for the FX pairs we need."""
    rates = {}
    for pair in FX_PAIRS:
        try:
            t = yf.Ticker(pair)
            price = float(t.fast_info.last_price)
            # e.g. AUDUSD=X  -> AUD_USD
            clean = pair.replace("=X", "")          # AUDUSD
            frm, to = clean[:3], clean[3:]           # AUD, USD
            rates[f"{frm}_{to}"] = round(price, 5)
            rates[f"{to}_{frm}"] = round(1 / price, 5)
            print(f"  FX {frm}/{to} = {price:.5f}")
        except Exception as e:
            print(f"  [ERROR] FX {pair}: {e}", file=sys.stderr)
        time.sleep(0.1)
    return rates


def main():
    print("=== MSP Portfolio Data Fetch ===")
    print(f"Started: {datetime.datetime.utcnow().isoformat()}Z\n")

    output = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "ohlc":   {},
        "quotes": {},
        "fx":     {},
    }

    print("── FX Rates ──")
    output["fx"] = fetch_fx()

    print("\n── OHLC + Quotes ──")
    for h in HOLDINGS:
        sym = h["sym"]
        print(f"\n{sym}")
        output["ohlc"][sym]   = fetch_ohlc(sym)
        output["quotes"][sym] = fetch_quote(sym)

    # Write output
    out_path = os.path.join(os.path.dirname(__file__), "..", "docs", "data.json")
    out_path = os.path.normpath(out_path)
    with open(out_path, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    size_kb = os.path.getsize(out_path) / 1024
    print(f"\n✓ Written {out_path}  ({size_kb:.1f} KB)")
    print(f"Finished: {datetime.datetime.utcnow().isoformat()}Z")


if __name__ == "__main__":
    main()
