"""
check_div_range.py - Check Dividend Ex-Dates Against Generated Daily Price Range

Reads generated CSV files and reports which dividend events fall within the
trading price series date bounds.
"""

import os
import sys
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYMBOL = sys.argv[1] if len(sys.argv) > 1 else "COMB.N0000"

daily_path = os.path.join(REPO_ROOT, f"{SYMBOL}_daily_with_dividends.csv")
divs_path = os.path.join(REPO_ROOT, f"{SYMBOL}_dividends.csv")

if not os.path.exists(daily_path) or not os.path.exists(divs_path):
    print(f"Error: Could not find '{daily_path}' or '{divs_path}'. Run cse_daily_dividends.py first.")
    sys.exit(1)

daily = pd.read_csv(daily_path)
divs = pd.read_csv(divs_path)

daily["date"] = pd.to_datetime(daily["date"])
divs["ex_date"] = pd.to_datetime(divs["ex_date"])

print("Daily Price Range:", daily["date"].min().date(), "to", daily["date"].max().date())
print(f"Total Trading Days: {len(daily)}")
print(f"Total Recorded Dividends: {len(divs)}")

in_range = divs[(divs["ex_date"] >= daily["date"].min()) & (divs["ex_date"] <= daily["date"].max())]
print(f"\nDividends falling strictly within price date range ({len(in_range)} records):")
print(in_range.to_string(index=False))

outside_range = divs[divs["ex_date"] < daily["date"].min()]
print(f"\nDividends predating price series ({len(outside_range)} records):")
print(outside_range.head(10).to_string(index=False))
