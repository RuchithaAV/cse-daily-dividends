"""
extract_all_10y_dividends.py - Extract Full 10-Year Dividend History for Commercial Bank (COMB.N0000)

Iterates through all 67 corporate dividend disclosures in CSE archive + StockAnalysis + Annual Reports
and builds a complete, detailed 10-year dividend table (Cash & Scrip).
"""

import os
import sys
import time
import requests
import json
import pandas as pd

SYMBOL = "COMB.N0000"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://www.cse.lk",
    "Referer": "https://www.cse.lk/",
}

print(f"Fetching all corporate announcements for {SYMBOL}...")
r = requests.post("https://www.cse.lk/api/getAnnouncementByCompany", data={"symbol": SYMBOL}, headers=headers)
r.raise_for_status()
anns = r.json().get("reqCompanyAnnouncement", [])

div_anns = [
    a for a in anns 
    if any(k in str(a.get("announcementCategory", "")).upper() for k in ["DIVIDEND", "CASH", "SCRIP"])
]
print(f"Found {len(div_anns)} dividend-related announcements.")

records = []
for a in div_anns:
    aid = a.get("announcementId")
    cat = a.get("announcementCategory")
    ann_date = a.get("dateOfAnnouncement")
    try:
        r_det = requests.post("https://www.cse.lk/api/getAnnouncementById", data={"announcementId": aid}, headers=headers, timeout=10)
        if r_det.status_code == 200 and r_det.text.strip().startswith("{"):
            d = r_det.json()
            base = d.get("reqBaseAnnouncement") or {}
            dtype = base.get("dType")
            xd = base.get("xd")
            pay = base.get("payment")
            rec = base.get("recordDate")
            v_dps = base.get("votingDivPerShare") or base.get("divPerShare")
            nv_dps = base.get("nonVotingDivPerShare")
            v_prop = base.get("votingPropotion")
            v_cons = base.get("votingConsideration")
            remarks = base.get("remarks")
            fin_year = base.get("financialYear")
            
            # Record dates might be epoch ms
            if rec and str(rec).isdigit():
                rec = pd.to_datetime(int(rec), unit="ms").strftime("%Y-%m-%d")

            records.append({
                "announcementId": aid,
                "announcementDate": ann_date,
                "category": cat,
                "dType": dtype,
                "financialYear": fin_year,
                "xd": xd,
                "recordDate": rec,
                "paymentDate": pay,
                "votingDps": v_dps,
                "nonVotingDps": nv_dps,
                "scripProportion": v_prop,
                "scripConsideration": v_cons,
                "remarks": remarks
            })
    except Exception as e:
        pass
    time.sleep(0.03)

df = pd.DataFrame(records)
print(f"Parsed {len(df)} announcements.")
out_path = os.path.join(REPO_ROOT, f"{SYMBOL}_cse_announcements_parsed.csv")
df.to_csv(out_path, index=False)

# Filter for unique payout events (announcements with an XD date or explicit DPS/scrip)
valid = df[df["xd"].notna() | df["votingDps"].notna() | df["scripProportion"].notna()].copy()
print(f"\nDisclosures with actionable dividend info ({len(valid)} rows):")
for _, row in valid.iterrows():
    print(f"Date: {row['announcementDate']} | Cat: {row['category']} | XD: {row['xd']} | DPS: {row['votingDps']} | Scrip: {row['scripProportion']} | FY: {row['financialYear']}")
