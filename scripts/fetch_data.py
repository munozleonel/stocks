#!/usr/bin/env python3
"""
fetch_data.py  —  fetches OHLC + quotes for MSP Portfolio holdings.
Writes docs/data.json consumed by the dashboard.
"""

import json, datetime, sys, os, time, math
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
                o,h,l,c = row["Open"], row["High"], row["Low"], row["Close"]
                if any(v is None or (isinstance(v,float) and math.isnan(v)) for v in (o,h,l,c)):
                    continue  # skip incomplete candles (holidays, thin trading, etc.) — NaN is not valid JSON
                candles.append({"t":int(ts.timestamp()*1000),
                    "o":round(float(o),4), "h":round(float(h),4),
                    "l":round(float(l),4),  "c":round(float(c),4)})
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
        price, prev = float(info.last_price), float(info.previous_close)
        if math.isnan(price) or math.isnan(prev):
            raise ValueError("NaN price/prev returned")
        return {"price":round(price,4), "prev":round(prev,4),
                "currency":getattr(info,"currency","USD")}
    except Exception as e:
        print(f"  [ERROR] quote {sym}: {e}", file=sys.stderr)
        return None


def fetch_fundamentals(sym):
    try:
        ticker = yf.Ticker(sym)
        info = ticker.info
        result = {
            "marketCap":    info.get("marketCap"),
            "pe":           info.get("trailingPE"),
            "forwardPe":    info.get("forwardPE"),
            "priceTarget":  info.get("targetMeanPrice"),
            "currency":     info.get("currency"),
        }
        dcf = calc_intrinsic_value(ticker, info)
        if dcf:
            result.update(dcf)
        return result
    except Exception as e:
        print(f"  [ERROR] fundamentals {sym}: {e}", file=sys.stderr)
        return None


# ── Buffett-style discounted cash flow ──────────────────────────────────────
# Simplified two-stage DCF on Free Cash Flow:
#   1. Take the company's most recent annual Free Cash Flow (FCF).
#   2. Project it forward DCF_YEARS, fading the growth rate linearly from
#      its own historical CAGR (clamped 2%-15%, i.e. never assume shrinkage
#      or hyper-growth) down to a conservative long-run TERMINAL_GROWTH.
#   3. Add a Gordon Growth terminal value for everything beyond year 10.
#   4. Discount it all back at DISCOUNT_RATE.
#   5. Divide by shares outstanding for intrinsic value per share.
# Only meaningful for real operating businesses with positive FCF — returns
# None for ETFs, crypto, and anything without a usable cash flow statement.
DCF_YEARS            = 10
DCF_DISCOUNT_RATE    = 0.09    # required rate of return
DCF_TERMINAL_GROWTH  = 0.025   # conservative long-run growth after year 10
DCF_MIN_GROWTH       = 0.02
DCF_MAX_GROWTH       = 0.15
DCF_MARGIN_OF_SAFETY = 0.25    # Graham/Buffett-style discount to fair value


def _annual_fcf_series(ticker):
    """Annual Free Cash Flow values, oldest → newest, or None if unavailable."""
    try:
        cf = ticker.cashflow
        if cf is None or cf.empty:
            return None
        row = None
        if "Free Cash Flow" in cf.index:
            row = cf.loc["Free Cash Flow"]
        else:
            op = next((cf.loc[l] for l in
                       ("Operating Cash Flow", "Total Cash From Operating Activities")
                       if l in cf.index), None)
            capex = next((cf.loc[l] for l in
                          ("Capital Expenditure", "Capital Expenditures")
                          if l in cf.index), None)
            if op is None or capex is None:
                return None
            row = op + capex  # capex is stored as a negative number
        vals = [float(v) for v in row.dropna().tolist()]
        vals.reverse()  # yfinance columns are newest → oldest; flip to oldest → newest
        return vals if len(vals) >= 2 else None
    except Exception:
        return None


def _cagr(vals):
    first, last = vals[0], vals[-1]
    years = len(vals) - 1
    if first <= 0 or last <= 0 or years <= 0:
        return None
    return (last / first) ** (1 / years) - 1


def calc_intrinsic_value(ticker, info):
    fcf_series = _annual_fcf_series(ticker)
    if not fcf_series:
        return None

    shares = info.get("sharesOutstanding")
    if not shares:
        return None

    latest_fcf = fcf_series[-1]
    if latest_fcf <= 0:
        return None  # can't meaningfully discount a currently cash-burning business

    growth = _cagr(fcf_series[-min(len(fcf_series), 6):])
    if growth is None:
        growth = DCF_TERMINAL_GROWTH
    growth = max(DCF_MIN_GROWTH, min(DCF_MAX_GROWTH, growth))

    pv_sum, fcf = 0.0, latest_fcf
    for yr in range(1, DCF_YEARS + 1):
        # fade the growth rate linearly toward the terminal rate over the projection window
        g = growth + (DCF_TERMINAL_GROWTH - growth) * (yr - 1) / (DCF_YEARS - 1)
        fcf *= (1 + g)
        pv_sum += fcf / ((1 + DCF_DISCOUNT_RATE) ** yr)

    terminal_value = fcf * (1 + DCF_TERMINAL_GROWTH) / (DCF_DISCOUNT_RATE - DCF_TERMINAL_GROWTH)
    pv_terminal = terminal_value / ((1 + DCF_DISCOUNT_RATE) ** DCF_YEARS)

    intrinsic_per_share = (pv_sum + pv_terminal) / shares

    return {
        "intrinsicValue":      round(intrinsic_per_share, 2),
        "marginOfSafetyValue": round(intrinsic_per_share * (1 - DCF_MARGIN_OF_SAFETY), 2),
    }


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
              "holdings": HOLDINGS, "ohlc":{}, "quotes":{}, "fx":{}, "fundamentals":{}}
    print("── FX ──")
    output["fx"] = fetch_fx()
    print("\n── OHLC + Quotes + Fundamentals ──")
    for h in HOLDINGS:
        sym = h["sym"]
        print(f"\n{sym}")
        output["ohlc"][sym]         = fetch_ohlc(sym)
        output["quotes"][sym]       = fetch_quote(sym)
        output["fundamentals"][sym] = fetch_fundamentals(sym)
        time.sleep(0.1)
    out = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "docs", "data.json"))
    try:
        # allow_nan=False makes this raise immediately if a NaN ever slips through,
        # instead of silently writing invalid JSON (JSON has no NaN token) that
        # breaks JSON.parse() in the browser.
        json_str = json.dumps(output, separators=(",",":"), allow_nan=False)
    except ValueError as e:
        print(f"\n✗ Refused to write data.json — output contains non-finite values: {e}", file=sys.stderr)
        sys.exit(1)  # leave the last known-good data.json in place rather than overwrite it
    with open(out, "w") as f:
        f.write(json_str)
    print(f"\n✓ {out}  ({os.path.getsize(out)/1024:.1f} KB)")

if __name__ == "__main__":
    main()
