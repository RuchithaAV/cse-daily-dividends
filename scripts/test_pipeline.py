"""
test_pipeline.py - End-to-End Pipeline Verification for CSE Daily Dividends

Validates:
1. CSE companyInfoSummery resolution to numeric stockId.
2. CSE Announcement API dividend extraction (/api/getAnnouncementByCompany & /api/getAnnouncementById).
3. StockAnalysis dividend scraping.
4. Historical manual dividend dictionary.
5. CSE companyChartDataByStock daily price retrieval (period=5).
6. Merging dividends onto matching trading days.
"""

import io
import json
import os
import re
import sys
import time
import requests
import pandas as pd
from datetime import datetime

SYMBOL = "COMB.N0000"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.cse.lk",
    "Referer": "https://www.cse.lk/",
}

# --------------------------------------------------------------------------
# MANUAL / ANNUAL REPORT DIVIDEND DICTIONARY (For historical dividends < 2022)
# --------------------------------------------------------------------------
MANUAL_DIVIDENDS = [
    {"ex_date": "2019-11-05", "record_date": "2019-11-07", "pay_date": "2019-11-18", "amount": 1.50, "source": "manual_annual_report"},
    {"ex_date": "2019-03-29", "record_date": "2019-04-02", "pay_date": "2019-04-18", "amount": 2.00, "source": "manual_annual_report"},
    {"ex_date": "2018-11-06", "record_date": "2018-11-08", "pay_date": "2018-11-20", "amount": 1.50, "source": "manual_annual_report"},
    {"ex_date": "2018-03-29", "record_date": "2018-04-03", "pay_date": "2018-04-20", "amount": 2.00, "source": "manual_annual_report"},
    {"ex_date": "2017-11-07", "record_date": "2017-11-09", "pay_date": "2017-11-21", "amount": 1.50, "source": "manual_annual_report"},
    {"ex_date": "2017-03-31", "record_date": "2017-04-04", "pay_date": "2017-04-21", "amount": 2.00, "source": "manual_annual_report"},
    {"ex_date": "2016-11-08", "record_date": "2016-11-10", "pay_date": "2016-11-22", "amount": 1.50, "source": "manual_annual_report"},
    {"ex_date": "2016-03-31", "record_date": "2016-04-04", "pay_date": "2016-04-22", "amount": 2.00, "source": "manual_annual_report"},
    {"ex_date": "2015-11-10", "record_date": "2015-11-12", "pay_date": "2015-11-24", "amount": 1.00, "source": "manual_annual_report"},
    {"ex_date": "2015-03-31", "record_date": "2015-04-06", "pay_date": "2015-04-24", "amount": 1.50, "source": "manual_annual_report"},
    {"ex_date": "2014-11-11", "record_date": "2014-11-13", "pay_date": "2014-11-25", "amount": 1.00, "source": "manual_annual_report"},
]

def parse_date_safe(val):
    if pd.isna(val) or val is None or str(val).strip() in ("", "-", "None"):
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

def fetch_cse_stock_id(symbol):
    url = "https://www.cse.lk/api/companyInfoSummery"
    r = requests.post(url, data={"symbol": symbol}, headers=HEADERS, timeout=20)
    print(f"CSE companyInfoSummery -> HTTP {r.status_code}")
    r.raise_for_status()
    data = r.json()
    info = data.get("reqSymbolInfo", {})
    stock_id = info.get("id")
    name = info.get("name")
    isin = info.get("isin")
    print(f"Resolved symbol {symbol} to CSE numeric stockId: {stock_id} ({name}, ISIN: {isin})")
    return stock_id

def fetch_cse_dividends(symbol):
    print(f"\n[Source 1: CSE Announcements API] Fetching dividends for {symbol}...")
    url = "https://www.cse.lk/api/getAnnouncementByCompany"
    r = requests.post(url, data={"symbol": symbol}, headers=HEADERS, timeout=20)
    print(f"CSE getAnnouncementByCompany -> HTTP {r.status_code}")
    r.raise_for_status()
    ann_list = r.json().get("reqCompanyAnnouncement", [])
    
    div_announcements = [
        a for a in ann_list 
        if any(term in str(a.get("announcementCategory", "")).upper() for term in ["DIVIDEND", "CASH"])
    ]
    print(f"Found {len(div_announcements)} dividend announcements in CSE archive.")
    
    records = []
    seen_ex_dates = set()
    for a in div_announcements:
        aid = a.get("announcementId")
        try:
            r_det = requests.post(
                "https://www.cse.lk/api/getAnnouncementById",
                data={"announcementId": aid},
                headers=HEADERS,
                timeout=15
            )
            if r_det.status_code == 200:
                base = r_det.json().get("reqBaseAnnouncement", {})
                xd_raw = base.get("xd")
                ex_date = parse_date_safe(xd_raw)
                
                v_dps = base.get("votingDivPerShare")
                if v_dps is None:
                    v_dps = base.get("divPerShare")
                if v_dps is None:
                    v_dps = base.get("nonVotingDivPerShare")
                
                try:
                    amount = float(v_dps) if v_dps is not None else None
                except (ValueError, TypeError):
                    amount = None
                
                rec_date = parse_date_safe(base.get("recordDate"))
                pay_date = parse_date_safe(base.get("payment"))
                
                if ex_date and amount is not None and ex_date not in seen_ex_dates:
                    seen_ex_dates.add(ex_date)
                    records.append({
                        "ex_date": ex_date,
                        "record_date": rec_date,
                        "pay_date": pay_date,
                        "amount": amount,
                        "source": "cse_api",
                    })
        except Exception as e:
            print(f"  Warning: failed fetching details for announcement {aid}: {e}")
        time.sleep(0.05)
    
    df = pd.DataFrame(records)
    print(f"CSE Announcements API yielded {len(df)} dividend payouts.")
    return df

def fetch_stockanalysis_dividends(symbol):
    print(f"\n[Source 2: StockAnalysis] Fetching dividends for {symbol}...")
    url = f"https://stockanalysis.com/quote/cose/{symbol}/dividend/"
    try:
        r = requests.get(url, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=20)
        print(f"StockAnalysis HTTP -> {r.status_code}")
        if r.status_code != 200:
            return pd.DataFrame()
        
        tables = pd.read_html(io.StringIO(r.text))
        if not tables:
            return pd.DataFrame()
        
        raw_df = tables[0]
        col_map = {}
        for c in raw_df.columns:
            cl = str(c).lower().strip()
            if "ex-div" in cl or "ex div" in cl:
                col_map[c] = "ex_date"
            elif "cash" in cl or "amount" in cl:
                col_map[c] = "amount"
            elif "record" in cl:
                col_map[c] = "record_date"
            elif "pay" in cl:
                col_map[c] = "pay_date"
        
        df = raw_df.rename(columns=col_map)
        records = []
        for _, row in df.iterrows():
            ex_date = parse_date_safe(row.get("ex_date"))
            rec_date = parse_date_safe(row.get("record_date"))
            pay_date = parse_date_safe(row.get("pay_date"))
            
            raw_amt = str(row.get("amount", "")).replace("LKR", "").replace("$", "").replace(",", "").strip()
            try:
                amt = float(raw_amt)
            except ValueError:
                amt = None
            
            if ex_date and amt is not None:
                records.append({
                    "ex_date": ex_date,
                    "record_date": rec_date,
                    "pay_date": pay_date,
                    "amount": amt,
                    "source": "stockanalysis",
                })
        
        res_df = pd.DataFrame(records)
        print(f"StockAnalysis yielded {len(res_df)} dividend payouts.")
        return res_df
    except Exception as e:
        print(f"StockAnalysis fetch failed: {e}")
        return pd.DataFrame()

def fetch_daily_prices(stock_id, symbol):
    print(f"\n[Daily Prices] Fetching from CSE API for stockId {stock_id} (symbol: {symbol})...")
    url = "https://www.cse.lk/api/companyChartDataByStock"
    r = requests.post(url, data={"stockId": stock_id, "period": 5}, headers=HEADERS, timeout=20)
    print(f"CSE companyChartDataByStock (period=5) -> HTTP {r.status_code}")
    r.raise_for_status()
    d = r.json()
    chart_data = d.get("chartData", [])
    print(f"Received {len(chart_data)} daily price records from CSE API.")
    if not chart_data:
        raise ValueError(f"No price records returned by CSE API for stockId {stock_id}")
    
    df = pd.DataFrame(chart_data)
    df["date"] = pd.to_datetime(df["t"], unit="ms").dt.tz_localize("UTC").dt.tz_convert("Asia/Colombo").dt.strftime("%Y-%m-%d")
    df["close"] = pd.to_numeric(df["p"], errors="coerce")
    df["volume"] = pd.to_numeric(df["q"], errors="coerce")
    daily = df[["date", "close", "volume"]].dropna(subset=["date"]).drop_duplicates("date").sort_values("date").reset_index(drop=True)
    return daily

def main():
    stock_id = fetch_cse_stock_id(SYMBOL)
    divs_cse = fetch_cse_dividends(SYMBOL)
    divs_sa = fetch_stockanalysis_dividends(SYMBOL)
    divs_manual = pd.DataFrame(MANUAL_DIVIDENDS)

    print("\n--- Summary of Dividend Sources ---")
    print("CSE API dividends count:", len(divs_cse))
    print("StockAnalysis dividends count:", len(divs_sa))
    print("Manual dividends count:", len(divs_manual))

    all_divs = pd.concat([divs_cse, divs_sa, divs_manual], ignore_index=True)
    all_divs = all_divs.sort_values(by=["ex_date", "source"], ascending=[False, True]).reset_index(drop=True)
    divs_csv_path = os.path.join(REPO_ROOT, f"{SYMBOL}_dividends.csv")
    all_divs.to_csv(divs_csv_path, index=False)
    print(f"\nSaved dividends CSV to {divs_csv_path} ({len(all_divs)} records)")
    print(all_divs.head(10))

    daily = fetch_daily_prices(stock_id, SYMBOL)
    print(f"Daily price range: {daily['date'].min()} to {daily['date'].max()} ({len(daily)} trading days)")

    source_columns = {
        "cse_api": "dps_cse",
        "stockanalysis": "dps_stockanalysis",
        "manual_annual_report": "dps_manual"
    }
    for col in source_columns.values():
        daily[col] = float("nan")

    daily_dates = pd.to_datetime(daily["date"])
    for _, row in all_divs.iterrows():
        ex_dt = pd.to_datetime(row["ex_date"])
        src = row.get("source")
        col_name = source_columns.get(src, f"dps_{src}")
        if col_name not in daily.columns:
            daily[col_name] = float("nan")
        amt = row["amount"]
        
        match_idx = daily.index[daily_dates >= ex_dt]
        if len(match_idx) > 0:
            target_idx = match_idx[0]
            # Ensure the matched trading date is within 7 days of ex-dividend date
            match_dt = daily_dates.iloc[target_idx]
            if (match_dt - ex_dt).days <= 7:
                daily.loc[target_idx, col_name] = amt

    daily_csv_path = os.path.join(REPO_ROOT, f"{SYMBOL}_daily_with_dividends.csv")
    daily.to_csv(daily_csv_path, index=False)
    print(f"\nSaved daily with dividends CSV to {daily_csv_path} ({len(daily)} rows)")

    div_days = daily[daily[list(source_columns.values())].notna().any(axis=1)]
    print(f"\nTrading days with marked dividend: {len(div_days)}")
    print(div_days[["date", "close", "volume", "dps_cse", "dps_stockanalysis", "dps_manual"]])

if __name__ == "__main__":
    main()
