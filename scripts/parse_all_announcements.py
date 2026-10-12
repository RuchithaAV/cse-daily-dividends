"""
parse_all_announcements.py - Parse All Corporate Dividend Disclosures for a CSE Symbol

Pulls the full announcement archive from /api/getAnnouncementByCompany, filters for
cash/dividend announcements, calls /api/getAnnouncementById for each disclosure,
and extracts xd (ex-dividend date), payment date, record date, and dividend per share.
"""

import os
import sys
import time
import requests
import json
import pandas as pd

SYMBOL = sys.argv[1] if len(sys.argv) > 1 else "COMB.N0000"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://www.cse.lk",
    "Referer": "https://www.cse.lk/",
}

print(f"Fetching announcements for symbol: {SYMBOL}...")
r = requests.post("https://www.cse.lk/api/getAnnouncementByCompany", data={"symbol": SYMBOL}, headers=headers)
r.raise_for_status()
ann_list = r.json().get("reqCompanyAnnouncement", [])

div_announcements = [
    a for a in ann_list 
    if any(term in str(a.get("announcementCategory", "")).upper() for term in ["DIVIDEND", "CASH"])
]
print(f"Total dividend announcements found: {len(div_announcements)}")

records = []
for a in div_announcements:
    aid = a.get("announcementId")
    cat = a.get("announcementCategory")
    ann_date = a.get("dateOfAnnouncement")
    try:
        r_det = requests.post("https://www.cse.lk/api/getAnnouncementById", data={"announcementId": aid}, headers=headers, timeout=10)
        if r_det.status_code == 200:
            base = r_det.json().get("reqBaseAnnouncement", {})
            dtype = base.get("dType")
            xd = base.get("xd")
            pay = base.get("payment")
            rec = base.get("recordDate")
            v_dps = base.get("votingDivPerShare") or base.get("divPerShare")
            nv_dps = base.get("nonVotingDivPerShare")
            remarks = base.get("remarks")
            records.append({
                "announcementId": aid,
                "announcementDate": ann_date,
                "category": cat,
                "dType": dtype,
                "xd": xd,
                "recordDate": rec,
                "payment": pay,
                "votingDps": v_dps,
                "nonVotingDps": nv_dps,
                "hasRemarks": bool(remarks)
            })
    except Exception as e:
        print(f"Error fetching {aid}: {e}")
    time.sleep(0.05)

df = pd.DataFrame(records)
print(f"Processed {len(df)} announcements.")
print("\nAnnouncements with XD date:")
with_xd = df[df["xd"].notna()]
print(with_xd[["announcementDate", "category", "dType", "xd", "votingDps", "payment"]])

print("\nAnnouncements with votingDps:")
with_dps = df[df["votingDps"].notna()]
print(with_dps[["announcementDate", "category", "dType", "xd", "votingDps", "payment"]])

out_csv = os.path.join(REPO_ROOT, f"{SYMBOL}_cse_announcements_parsed.csv")
df.to_csv(out_csv, index=False)
print(f"\nSaved full announcement breakdown to: {out_csv}")
