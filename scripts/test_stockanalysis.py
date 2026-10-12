"""
test_stockanalysis.py - Scrape & Verify Dividend Data from StockAnalysis.com

Queries stockanalysis.com/quote/cose/<SYMBOL>/dividend/ using plain HTTP + pandas.read_html
to parse historical declared dividends.
"""

import sys
import io
import requests
import pandas as pd

SYMBOL = sys.argv[1] if len(sys.argv) > 1 else "COMB.N0000"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# 1. Test StockAnalysis dividend page
url_div = f"https://stockanalysis.com/quote/cose/{SYMBOL}/dividend/"
print(f"Requesting StockAnalysis dividend page: {url_div}")
r_div = requests.get(url_div, headers=headers, timeout=20)
print("HTTP Status:", r_div.status_code)

if r_div.status_code == 200:
    dfs = pd.read_html(io.StringIO(r_div.text))
    print(f"Tables found: {len(dfs)}")
    for i, df in enumerate(dfs):
        print(f"\n--- Table {i} ---")
        print(df.head(10))
else:
    print("Could not retrieve dividend table. Page content snippet:", r_div.text[:300])

# 2. Test StockAnalysis history page
url_hist = f"https://stockanalysis.com/quote/cose/{SYMBOL}/history/"
print(f"\nRequesting StockAnalysis history page: {url_hist}")
r_hist = requests.get(url_hist, headers=headers, timeout=20)
print("HTTP Status:", r_hist.status_code)
if r_hist.status_code == 200:
    try:
        dfs_h = pd.read_html(io.StringIO(r_hist.text))
        print(f"History tables found: {len(dfs_h)}")
        for i, df in enumerate(dfs_h):
            print(f"\n--- History Table {i} ---")
            print(df.head(5))
    except Exception as e:
        print("No tables parsed from history page:", e)
