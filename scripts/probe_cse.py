"""
probe_cse.py - Probe Colombo Stock Exchange Server Headers & Endpoint Status

Tests connection, user agent handling, and companyInfoSummery response structure.
"""

import sys
import requests
import json

SYMBOL = sys.argv[1] if len(sys.argv) > 1 else "COMB.N0000"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.cse.lk",
    "Referer": f"https://www.cse.lk/company-profile?symbol={SYMBOL}",
}

print(f"--- Probing companyInfoSummery for symbol: {SYMBOL} ---")
try:
    r = requests.post("https://www.cse.lk/api/companyInfoSummery", data={"symbol": SYMBOL}, headers=headers, timeout=20)
    print("HTTP Status Code:", r.status_code)
    data = r.json()
    print("Response Top-Level Keys:", list(data.keys()) if isinstance(data, dict) else f"List length: {len(data)}")
    if isinstance(data, dict):
        for k, v in data.items():
            if not isinstance(v, (dict, list)):
                print(f"  {k}: {v}")
            elif isinstance(v, dict):
                print(f"  {k} (keys): {list(v.keys())}")
                for subk, subv in v.items():
                    if any(term in subk.lower() for term in ["id", "symbol", "name", "isin"]):
                        print(f"    {subk}: {subv}")
except Exception as e:
    print("Probe error:", e)
