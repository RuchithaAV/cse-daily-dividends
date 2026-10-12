"""
test_daily_format.py - Verify CSE OHLC Millisecond Timestamp Parsing & Timezone Localization

Queries CSE companyChartDataByStock with period=5 (52 weeks / 1 year),
localizes timestamps to Sri Lanka Standard Time (Asia/Colombo / UTC+05:30),
and extracts date, close, and volume columns.
"""

import sys
import pandas as pd
import requests

SYMBOL = sys.argv[1] if len(sys.argv) > 1 else "COMB.N0000"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://www.cse.lk",
    "Referer": "https://www.cse.lk/",
}

# Resolve stockId
r_info = requests.post("https://www.cse.lk/api/companyInfoSummery", data={"symbol": SYMBOL}, headers=headers)
stock_id = 208
if r_info.status_code == 200:
    stock_id = r_info.json().get("reqSymbolInfo", {}).get("id", 208)

print(f"Fetching 1-year daily chart data for stockId {stock_id} ({SYMBOL})...")
r = requests.post("https://www.cse.lk/api/companyChartDataByStock", data={"stockId": stock_id, "period": 5}, headers=headers)
data = r.json().get("chartData", [])
df = pd.DataFrame(data)

df["date"] = pd.to_datetime(df["t"], unit="ms").dt.tz_localize("UTC").dt.tz_convert("Asia/Colombo").dt.strftime("%Y-%m-%d")
df["close"] = pd.to_numeric(df["p"], errors="coerce")
df["volume"] = pd.to_numeric(df["q"], errors="coerce")

daily = df[["date", "close", "volume"]].drop_duplicates("date").sort_values("date").reset_index(drop=True)
print(f"Daily table rows: {len(daily)}")
print(f"Date range: {daily['date'].min()} to {daily['date'].max()}")
print("\n--- First 3 Trading Days ---")
print(daily.head(3))
print("\n--- Last 3 Trading Days ---")
print(daily.tail(3))
