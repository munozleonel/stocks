#!/usr/bin/env python3
"""
fetch_data.py  —  fetches OHLC + quotes for MSP Portfolio holdings.
Writes docs/data.json consumed by the dashboard.
"""

import json, datetime, sys, os, time
import yfinance as yf

HOLDINGS = [
    # ── Australia ──────────────────────────────────────────────────────────────
    {"sym":"A2M.AX",  "name":"A2 Milk Co.",              "region":"Australia", "shares":220.0,   "avgCost":9.2684,   "currency":"AUD"},
    {"sym":"NCK.AX",  "name":"Nick Scali Ltd.",           "region":"Australia", "shares":155.0,   "avgCost":6.5000,   "currency":"AUD"},
    {"sym":"VAS.AX",  "name":"Vanguard Aust Shares ETF",  "region":"Australia", "shares":10.0,    "avgCost":72.8500,  "currency":"AUD"},
    {"sym":"WBC.AX",  "name":"Westpac Banking Corp.",     "region":"Australia", "shares":36.0,    "avgCost":27.8000,  "currency":"AUD"},
    # ── China ─────────────────────────────────────────────────────────────────
    {"sym":"BABA",    "name":"Alibaba Group Holding",     "region":"China",     "shares":23.0,    "avgCost":166.4426, "currency":"USD"},
    {"sym":"CQQQ",    "name":"Invesco China Tech ETF",    "region":"China",     "shares":20.0,    "avgCost":66.7000,  "currency":"USD"},
    # ── Crypto ────────────────────────────────────────────────────────────────
    {"sym":"ETH-AUD", "name":"Ethereum",                  "region":"Crypto",    "shares":1.12,    "avgCost":1000.0,   "currency":"AUD"},
    # ── Europe ────────────────────────────────────────────────────────────────
    {"sym":"CAP.PA",  "name":"Capgemini",                 "region":"Europe",    "shares":27.8578, "avgCost":90.4557,  "currency":"EUR"},
    # ── US ────────────────────────────────────────────────────────────────────
    {"sym":"AAPL",    "name":"Apple Inc.",                "region":"US",        "shares":4.0,     "avgCost":60.0000,  "currency":"USD"},
    {"sym":"AMZN",    "name":"Amazon.com, Inc.",          "region":"US",        "shares":8.9087,  "avgCost":112.2500, "currency":"USD"},
    {"sym":"BA",      "name":"Boeing Company (The)",      "region":"US",        "shares":6.0,     "avgCost":174.4433, "currency":"USD"},
    {"sym":"BRK-B",   "name":"Berkshire Hathaway Inc.",   "region":"US",        "shares":2.0,     "avgCost":177.1200, "currency":"USD"},
    {"sym":"COIN",    "name":"Coinbase Global, Inc.",     "region":"US",        "shares":9.0,     "avgCost":166.2911, "currency":"USD"},
    {"sym":"CRSR",    "name":"Corsair Gaming, Inc.",      "region":"US",        "shares":36.93,   "avgCost":36.0049,  "currency":"USD"},
    {"sym":"META",    "name":"Meta Platforms, Inc.",      "region":"US",        "shares":15.0007, "avgCost":189.5068, "currency":"USD"},
    {"sym":"MU",      "name":"Micron Technology, Inc.",   "region":"US",        "shares":5.0,     "avgCost":59.3700,  "currency":"USD"},
    {"sym":"NFLX",    "name":"Netflix, Inc.",             "region":"US",        "shares":20.0,    "avgCost":38.2000,  "currency":"USD"},
    {"sym":"TSLA",    "name":"Tesla, Inc.",               "region":"US",        "shares":83.7733, "avgCost":16.1610,  "currency":"USD"},
    {"sym":"UNH",     "name":"UnitedHealth Group",        "region":"US",        "shares":4.0,     "avgCost":230.9125, "currency":"USD"},
    {"sym":"V",       "name":"Visa Inc.",                 "region":"US",        "shares":3.0,     "avgCost":209.2633, "currency":"USD"},
]

FX_PAIRS = ["AUDUSD=X", "EURUSD=X", "EURAUD=X"]
RANGE_MAP = {"7D":("7d","1d"), "3M":("3mo","1d"), "12M":("1y","1d")}


def fetch_ohlc(sym):
    result = {}
    ticker = yf.Ticker(sym)
    for key, (period, interval) in RANGE_MAP.items():
        try:
            df = ticker.history(period=period, interval=interval, auto_adjust=True)
            if df.empty:
                result[key] = []; continue
            candles = []
            for ts, row in df.iterrows():
                candles.append({"t":int(ts.timestamp()*1000),
                    "o":round(float(row["Open"]),4), "h":round(float(row["High"]),4),
                    "l":round(float(row["Low"]),4),  "c":round(float(row["Close"]),4)})
            result[key] = candles
            print(f"  {sym:12s} {key:4s}  {len(candles)} candles")
        except Exception as e:
            print(f"  [ERROR] {sym} {key}: {e}", file=sys.stderr)
            result[key] = []
        time.sleep(0.1)
    return result


def fetch_quote(sym):
    try:
        info = yf.Ticker(sym).fast_info
        return {"price":round(float(info.last_price),4),
                "prev":round(float(info.previous_close),4),
                "currency":getattr(info,"currency","USD")}
    except Exception as e:
        print(f"  [ERROR] quote {sym}: {e}", file=sys.stderr)
        return None


def fetch_fx():
    rates = {}
    for pair in FX_PAIRS:
        try:
            price = float(yf.Ticker(pair).fast_info.last_price)
            frm, to = pair[:3], pair[3:6]
            rates[f"{frm}_{to}"] = round(price, 5)
            rates[f"{to}_{frm}"] = round(1/price, 5)
            print(f"  FX {frm}/{to} = {price:.5f}")
        except Exception as e:
            print(f"  [ERROR] FX {pair}: {e}", file=sys.stderr)
        time.sleep(0.1)
    return rates


def main():
    print(f"=== MSP Portfolio Fetch  {datetime.datetime.utcnow().isoformat()}Z ===\n")
    output = {"generated_at": datetime.datetime.utcnow().isoformat()+"Z",
              "holdings": HOLDINGS, "ohlc":{}, "quotes":{}, "fx":{}}
    print("── FX ──")
    output["fx"] = fetch_fx()
    print("\n── OHLC + Quotes ──")
    for h in HOLDINGS:
        sym = h["sym"]
        print(f"\n{sym}")
        output["ohlc"][sym]   = fetch_ohlc(sym)
        output["quotes"][sym] = fetch_quote(sym)
    out = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "docs", "data.json"))
    with open(out, "w") as f:
        json.dump(output, f, separators=(",",":"))
    print(f"\n✓ {out}  ({os.path.getsize(out)/1024:.1f} KB)")

if __name__ == "__main__":
    main()
