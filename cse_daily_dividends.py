#!/usr/bin/env python3
"""
cse_daily_dividends.py - Colombo Stock Exchange (CSE) Daily Prices & Dividend Mapper

Produces a daily trading table with dividend amounts marked on each ex-dividend date,
along with a consolidated dividends-only CSV.

Constraints & Features:
- Plain HTTP requests only (no Selenium, Playwright, or Chromium).
- Fully compatible with Python 3.13 and Google Colab (Ubuntu 24.04).
- Polite request pacing with User-Agent and timeouts.
- Configurable symbol (default: COMB.N0000).
- Multiple dividend sources (CSE Announcements API, StockAnalysis, and Manual/Annual Reports dict).
- Auto-resolves numeric CSE stockId from companyInfoSummery.
- Fetches daily OHLC from CSE API companyChartDataByStock (or optional local CSV for extended 10y history).
"""

import os
import io
import sys
import time
import argparse
import requests
import pandas as pd
from datetime import datetime

# ==============================================================================
# CONFIGURATION & PARAMETERS
# ==============================================================================
DEFAULT_SYMBOL = "COMB.N0000"
DEFAULT_YEARS = 10

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.cse.lk",
    "Referer": "https://www.cse.lk/",
}

# ------------------------------------------------------------------------------
# MANUAL / ANNUAL REPORT DIVIDEND DICTIONARY
# ------------------------------------------------------------------------------
# Add or modify older dividends here (e.g., prior to 2022 from company Annual Reports).
# Format: {"ex_date": "YYYY-MM-DD", "record_date": "YYYY-MM-DD", "pay_date": "YYYY-MM-DD", "amount": float, "source": str}
MANUAL_DIVIDENDS = {
    "COMB.N0000": [
        {"ex_date": "2019-11-05", "record_date": "2019-11-07", "pay_date": "2019-11-18", "amount": 1.50, "source": "annual_report_2019"},
        {"ex_date": "2019-03-29", "record_date": "2019-04-02", "pay_date": "2019-04-18", "amount": 2.00, "source": "annual_report_2018_final"},
        {"ex_date": "2018-11-06", "record_date": "2018-11-08", "pay_date": "2018-11-20", "amount": 1.50, "source": "annual_report_2018_interim"},
        {"ex_date": "2018-03-29", "record_date": "2018-04-03", "pay_date": "2018-04-20", "amount": 2.00, "source": "annual_report_2017_final"},
        {"ex_date": "2017-11-07", "record_date": "2017-11-09", "pay_date": "2017-11-21", "amount": 1.50, "source": "annual_report_2017_interim"},
        {"ex_date": "2017-03-31", "record_date": "2017-04-04", "pay_date": "2017-04-21", "amount": 2.00, "source": "annual_report_2016_final"},
        {"ex_date": "2016-11-08", "record_date": "2016-11-10", "pay_date": "2016-11-22", "amount": 1.50, "source": "annual_report_2016_interim"},
        {"ex_date": "2016-03-31", "record_date": "2016-04-04", "pay_date": "2016-04-22", "amount": 2.00, "source": "annual_report_2015_final"},
        {"ex_date": "2015-11-10", "record_date": "2015-11-12", "pay_date": "2015-11-24", "amount": 1.00, "source": "annual_report_2015_interim"},
        {"ex_date": "2015-03-31", "record_date": "2015-04-06", "pay_date": "2015-04-24", "amount": 1.50, "source": "annual_report_2014_final"},
        {"ex_date": "2014-11-11", "record_date": "2014-11-13", "pay_date": "2014-11-25", "amount": 1.00, "source": "annual_report_2014_interim"},
    ]
}


def parse_date_safe(val):
    """Safely convert timestamps, epoch ms, or date strings to YYYY-MM-DD."""
    if pd.isna(val) or val is None or str(val).strip() in ("", "-", "None", "nan"):
        return None
    val_str = str(val).strip()
    if val_str.replace(".", "").isdigit():
        num = float(val_str)
        unit = "ms" if num > 1e11 else "s"
        return pd.to_datetime(num, unit=unit).strftime("%Y-%m-%d")
    try:
        dt = pd.to_datetime(val_str, errors="coerce")
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


# ==============================================================================
# CSE API RESOLUTION
# ==============================================================================
def get_cse_stock_id(symbol):
    """
    Look up the internal CSE numeric stockId using companyInfoSummery.
    Note: CSE Spring backend requires application/x-www-form-urlencoded data.
    """
    url = "https://www.cse.lk/api/companyInfoSummery"
    print(f"\n[CSE API] Resolving numeric stockId for symbol '{symbol}'...")
    try:
        r = requests.post(url, data={"symbol": symbol}, headers=HEADERS, timeout=25)
        print(f"  POST /api/companyInfoSummery -> HTTP {r.status_code}")
        r.raise_for_status()
        data = r.json()
        info = data.get("reqSymbolInfo", {})
        stock_id = info.get("id")
        isin = info.get("isin")
        name = info.get("name")
        print(f"  Name: {name} | ISIN: {isin} | stockId: {stock_id}")
        return stock_id
    except Exception as e:
        print(f"  Warning: Failed to fetch stockId for {symbol}: {e}")
        return None


# ==============================================================================
# DIVIDEND FETCHERS
# ==============================================================================
def fetch_cse_api_dividends(symbol):
    """
    Fetches official corporate dividend announcements from the CSE archive.
    Uses /api/getAnnouncementByCompany followed by /api/getAnnouncementById.
    """
    print(f"\n[Source 1: CSE Announcements API] Fetching dividend disclosures for '{symbol}'...")
    url = "https://www.cse.lk/api/getAnnouncementByCompany"
    try:
        r = requests.post(url, data={"symbol": symbol}, headers=HEADERS, timeout=25)
        print(f"  POST /api/getAnnouncementByCompany -> HTTP {r.status_code}")
        r.raise_for_status()
        ann_list = r.json().get("reqCompanyAnnouncement", [])
        div_ann = [a for a in ann_list if "DIVIDEND" in str(a.get("announcementCategory", "")).upper()]
        print(f"  Found {len(div_ann)} dividend announcements in company archive.")
    except Exception as e:
        print(f"  CSE Announcements API request failed: {e}")
        return pd.DataFrame(columns=["ex_date", "record_date", "pay_date", "amount", "source"])

    rows = []
    for a in div_ann:
        aid = a.get("announcementId")
        if not aid:
            continue
        try:
            r_det = requests.post(
                "https://www.cse.lk/api/getAnnouncementById",
                data={"announcementId": aid},
                headers=HEADERS,
                timeout=12
            )
            if r_det.status_code == 200:
                base = r_det.json().get("reqBaseAnnouncement", {})
                xd = parse_date_safe(base.get("xd"))
                rec = parse_date_safe(base.get("recordDate"))
                pay = parse_date_safe(base.get("payment"))
                amt = base.get("votingDivPerShare") or base.get("divPerShare")
                if amt is not None:
                    try:
                        amt = float(amt)
                    except (ValueError, TypeError):
                        amt = None

                if xd and amt and amt > 0:
                    rows.append({
                        "ex_date": xd,
                        "record_date": rec,
                        "pay_date": pay,
                        "amount": amt,
                        "source": "cse_api",
                    })
        except Exception:
            pass
        # Polite delay between individual detail requests
        time.sleep(0.04)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by=["ex_date", "amount"], ascending=[False, False]).drop_duplicates(subset=["ex_date"])
        df = df[["ex_date", "record_date", "pay_date", "amount", "source"]].reset_index(drop=True)
    print(f"  Extracted {len(df)} verified dividend records from CSE API.")
    return df


def fetch_stockanalysis_dividends(symbol):
    """
    Fetches dividends from StockAnalysis (covers ~4 recent years).
    Uses plain HTTP requests with pandas.read_html / BeautifulSoup.
    """
    print(f"\n[Source 2: StockAnalysis] Fetching dividends for '{symbol}'...")
    url = f"https://stockanalysis.com/quote/cose/{symbol}/dividend/"
    try:
        r = requests.get(url, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=25)
        print(f"  GET {url} -> HTTP {r.status_code}")
        r.raise_for_status()
        dfs = pd.read_html(io.StringIO(r.text))
        for t in dfs:
            cols = [str(c).lower() for c in t.columns]
            if any("ex-div" in c for c in cols) and any("amount" in c for c in cols):
                t.columns = cols
                c_ex = next(c for c in cols if "ex-div" in c)
                c_amt = next(c for c in cols if "amount" in c)
                c_rec = next((c for c in cols if "record" in c), None)
                c_pay = next((c for c in cols if "pay" in c), None)

                out = pd.DataFrame()
                out["ex_date"] = t[c_ex].apply(parse_date_safe)
                out["amount"] = pd.to_numeric(t[c_amt].astype(str).str.extract(r"([0-9.]+)")[0], errors="coerce")
                out["record_date"] = t[c_rec].apply(parse_date_safe) if c_rec else None
                out["pay_date"] = t[c_pay].apply(parse_date_safe) if c_pay else None
                out["source"] = "stockanalysis"
                out = out.dropna(subset=["ex_date", "amount"]).sort_values(by="ex_date", ascending=False).reset_index(drop=True)
                print(f"  Extracted {len(out)} dividend records from StockAnalysis.")
                return out[["ex_date", "record_date", "pay_date", "amount", "source"]]
    except Exception as e:
        print(f"  Warning: StockAnalysis dividends unavailable: {e}")
    return pd.DataFrame(columns=["ex_date", "record_date", "pay_date", "amount", "source"])


def get_manual_dividends(symbol):
    """Retrieves pre-configured manual/annual report dividend records for the symbol."""
    records = MANUAL_DIVIDENDS.get(symbol, [])
    df = pd.DataFrame(records)
    if not df.empty:
        df["ex_date"] = df["ex_date"].apply(parse_date_safe)
        df["record_date"] = df["record_date"].apply(parse_date_safe)
        df["pay_date"] = df["pay_date"].apply(parse_date_safe)
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df["source"] = "manual"
        df = df[["ex_date", "record_date", "pay_date", "amount", "source"]].dropna(subset=["ex_date", "amount"])
    else:
        df = pd.DataFrame(columns=["ex_date", "record_date", "pay_date", "amount", "source"])
    print(f"\n[Source 3: Manual / Annual Reports] Loaded {len(df)} historical dividend records.")
    return df


# ==============================================================================
# DAILY PRICE DATA FETCHER
# ==============================================================================
def fetch_daily_prices(stock_id, symbol, csv_path=None, years=10):
    """
    Fetches daily price history:
    1. If `csv_path` is specified and exists, loads the extended 10y dataset from CSV.
    2. Otherwise, queries CSE API /api/companyChartDataByStock with period=5 (1-year daily OHLC).
    """
    if csv_path and os.path.exists(csv_path):
        print(f"\n[Daily Prices] Loading historical price data from local CSV: {csv_path}")
        df_csv = pd.read_csv(csv_path)
        d_col = next((c for c in df_csv.columns if any(k in c.lower() for k in ["date", "time"])), None)
        c_col = next((c for c in df_csv.columns if any(k in c.lower() for k in ["close", "price", "ltp", "last"])), None)
        v_col = next((c for c in df_csv.columns if any(k in c.lower() for k in ["volume", "qty", "share"])), None)

        if not d_col or not c_col:
            raise ValueError(f"Could not find required date and close price columns in {csv_path}")

        daily = pd.DataFrame({
            "date": df_csv[d_col].apply(parse_date_safe),
            "close": pd.to_numeric(df_csv[c_col], errors="coerce"),
            "volume": pd.to_numeric(df_csv[v_col], errors="coerce") if v_col else 0.0
        })
        daily = daily.dropna(subset=["date", "close"]).drop_duplicates("date").sort_values("date").reset_index(drop=True)
        print(f"  Loaded {len(daily)} trading days from CSV.")
        return daily

    # Fallback to public CSE API endpoint
    if not stock_id:
        raise ValueError(f"Cannot query CSE price API without valid stockId for {symbol}")

    print(f"\n[Daily Prices] Querying CSE API companyChartDataByStock for stockId {stock_id} (symbol: {symbol})...")
    url = "https://www.cse.lk/api/companyChartDataByStock"
    # Period 5 returns 1-year daily history (~241 trading days)
    r = requests.post(url, data={"stockId": stock_id, "period": 5}, headers=HEADERS, timeout=25)
    print(f"  POST /api/companyChartDataByStock (period=5) -> HTTP {r.status_code}")
    r.raise_for_status()

    chart_data = r.json().get("chartData", [])
    if not chart_data:
        raise ValueError(f"CSE API returned 0 chart records for stockId {stock_id}.")

    df = pd.DataFrame(chart_data)
    # Timestamps in ms; convert to Sri Lankan local date
    df["date"] = pd.to_datetime(df["t"], unit="ms").dt.tz_localize("UTC").dt.tz_convert("Asia/Colombo").dt.strftime("%Y-%m-%d")
    df["close"] = pd.to_numeric(df["p"], errors="coerce")
    df["volume"] = pd.to_numeric(df["q"], errors="coerce").fillna(0)

    daily = df[["date", "close", "volume"]].dropna(subset=["date", "close"]).drop_duplicates("date").sort_values("date").reset_index(drop=True)
    print(f"  Retrieved {len(daily)} daily trading records from CSE API ({daily['date'].min()} to {daily['date'].max()}).")
    return daily


# ==============================================================================
# MERGING & OUTPUT
# ==============================================================================
def merge_dividends_to_daily(daily_df, div_df, col_name, max_days_ahead=7):
    """
    Fills `col_name` with the dividend amount ONLY on the first trading day
    on or after each ex-dividend date.
    A matching threshold `max_days_ahead` (default: 7 calendar days) prevents
    mapping historical dividends from earlier years onto Day 1 when dataset starts later.
    """
    daily_df[col_name] = float("nan")
    if div_df.empty:
        return

    daily_dates = pd.to_datetime(daily_df["date"])
    for _, row in div_df.iterrows():
        ex_dt = pd.to_datetime(row["ex_date"])
        amt = row["amount"]
        future_idx = daily_df.index[daily_dates >= ex_dt]
        if len(future_idx) > 0:
            target_idx = future_idx[0]
            target_dt = daily_dates.loc[target_idx]
            diff_days = (target_dt - ex_dt).days
            if diff_days <= max_days_ahead:
                daily_df.loc[target_idx, col_name] = amt


def run_pipeline(symbol=DEFAULT_SYMBOL, years=DEFAULT_YEARS, csv_path=None, output_dir="."):
    os.makedirs(output_dir, exist_ok=True)
    print("=" * 75)
    print(f"CSE Daily Dividends Pipeline | Symbol: {symbol} | Target Window: {years}y")
    print("=" * 75)

    # 1. Resolve numeric stock ID
    stock_id = get_cse_stock_id(symbol)

    # 2. Fetch dividend sources
    divs_cse = fetch_cse_api_dividends(symbol)
    divs_sa = fetch_stockanalysis_dividends(symbol)
    divs_man = get_manual_dividends(symbol)

    # 3. Consolidate separate dividends-only table
    all_divs = pd.concat([divs_cse, divs_sa, divs_man], ignore_index=True)
    if not all_divs.empty:
        all_divs = all_divs.sort_values(by=["ex_date", "source"], ascending=[False, True]).reset_index(drop=True)

    divs_filename = f"{symbol}_dividends.csv"
    divs_path = os.path.join(output_dir, divs_filename)
    all_divs.to_csv(divs_path, index=False)
    print(f"\n[Saved] Dividends-only file: {divs_path} ({len(all_divs)} records)")

    # 4. Fetch daily price series
    daily = fetch_daily_prices(stock_id, symbol, csv_path=csv_path, years=years)

    # 5. Merge each source into its own column
    source_map = [
        (divs_cse, "dps_cse"),
        (divs_sa, "dps_stockanalysis"),
        (divs_man, "dps_manual"),
    ]
    for d_df, col_name in source_map:
        merge_dividends_to_daily(daily, d_df, col_name)

    # 6. Save daily table with dividends
    daily_filename = f"{symbol}_daily_with_dividends.csv"
    daily_path = os.path.join(output_dir, daily_filename)
    daily.to_csv(daily_path, index=False)
    print(f"[Saved] Daily table with dividends: {daily_path} ({len(daily)} rows)")

    # 7. Print Diagnostics
    dps_cols = [col for _, col in source_map]
    div_days = daily[daily[dps_cols].notna().any(axis=1)]
    print("\n" + "=" * 75)
    print("PIPELINE SUMMARY & DIAGNOSTICS")
    print("=" * 75)
    print(f"Stock Symbol:          {symbol}")
    print(f"CSE Stock ID:          {stock_id}")
    print(f"Daily Trading Days:    {len(daily)} rows")
    print(f"Date Span:             {daily['date'].min()} to {daily['date'].max()}")
    print(f"Total Dividend Events: {len(all_divs)} records across sources")
    print(f"Trading Days w/ Divs:  {len(div_days)} days marked in price series")
    if not div_days.empty:
        print("\nTrading Days with Marked Dividends:")
        print(div_days[["date", "close", "volume"] + dps_cols].to_string(index=False))
    print("=" * 75)

    return daily, all_divs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CSE Daily Stock Price & Dividend Table Generator")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL, help="CSE Ticker Symbol (default: COMB.N0000)")
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS, help="Target history in years (default: 10)")
    parser.add_argument("--csv", default=None, help="Optional path to local historical prices CSV")
    parser.add_argument("--output-dir", default=".", help="Directory to save CSV outputs")
    args = parser.parse_args()

    run_pipeline(symbol=args.symbol, years=args.years, csv_path=args.csv, output_dir=args.output_dir)
