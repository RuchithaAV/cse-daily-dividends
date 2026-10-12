"""
test_cse_endpoints.py - Validate Colombo Stock Exchange API Endpoints & Request Formats

Tests:
1. companyChartDataByStock with stockId and period codes (1, 2, 3, 5, etc.)
2. charts endpoint (testing date bounds and period parameters)
3. charts/52week endpoint
4. getAnnouncementByCompany endpoint
"""

import requests
import json
import sys

SYMBOL = sys.argv[1] if len(sys.argv) > 1 else "COMB.N0000"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://www.cse.lk",
    "Referer": "https://www.cse.lk/",
}

def post_form(endpoint, data):
    url = f"https://www.cse.lk/api/{endpoint}"
    r = requests.post(url, data=data, headers=headers, timeout=20)
    print(f"POST {endpoint} with {data} -> HTTP {r.status_code}")
    try:
        j = r.json()
        if isinstance(j, dict):
            print("  Keys:", list(j.keys())[:10])
            for k, v in list(j.items())[:3]:
                if isinstance(v, list):
                    print(f"  {k}: list of {len(v)} items")
                    if v:
                        print(f"    sample item 0: {v[0]}")
                        print(f"    sample item -1: {v[-1]}")
                else:
                    print(f"  {k}: {str(v)[:150]}")
        elif isinstance(j, list):
            print(f"  List of {len(j)} items")
            if j:
                print(f"  sample item 0: {j[0]}")
                print(f"  sample item -1: {j[-1]}")
        else:
            print("  Response:", str(j)[:200])
    except Exception as e:
        print("  Text response:", r.text[:200])
    print("-" * 50)
    return r

if __name__ == "__main__":
    # Resolve numeric stockId first
    r_info = requests.post("https://www.cse.lk/api/companyInfoSummery", data={"symbol": SYMBOL}, headers=headers)
    stock_id = 208
    if r_info.status_code == 200:
        stock_id = r_info.json().get("reqSymbolInfo", {}).get("id", 208)
    print(f"Testing with symbol '{SYMBOL}' and stockId '{stock_id}':\n")

    # 1. Test companyChartDataByStock with different period values
    for period in [1, 2, 3, 5, 10]:
        post_form("companyChartDataByStock", {"stockId": stock_id, "period": period})

    # 2. Test charts endpoint: symbol, fromDate, toDate, period
    for period in ["1D", "1M", "1Y", "5Y", "ALL", 1, "D"]:
        post_form("charts", {"symbol": SYMBOL, "fromDate": "2014-01-01", "toDate": "2026-04-01", "period": period})

    # 3. Test charts/52week
    post_form("charts/52week", {"symbol": SYMBOL})

    # 4. Test getAnnouncementByCompany
    post_form("getAnnouncementByCompany", {"symbol": SYMBOL})
