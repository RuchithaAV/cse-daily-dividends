"""
inspect_div_announcements.py - Inspect CSE Dividend Announcements Metadata & Attachments

Queries /api/getAnnouncementByCompany and inspects /api/getAnnouncementById for the
first 5 dividend disclosures to examine fields (xd, recordDate, payment, votingDivPerShare, docs).
"""

import sys
import requests
import json
import pandas as pd

SYMBOL = sys.argv[1] if len(sys.argv) > 1 else "COMB.N0000"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://www.cse.lk",
    "Referer": "https://www.cse.lk/",
}

print(f"Inspecting announcements for symbol: {SYMBOL}...")
r = requests.post("https://www.cse.lk/api/getAnnouncementByCompany", data={"symbol": SYMBOL}, headers=headers)
ann_list = r.json().get("reqCompanyAnnouncement", [])

cash_divs = [
    a for a in ann_list 
    if any(term in str(a.get("announcementCategory", "")).upper() for term in ["CASH", "DIVIDEND"])
]
print(f"Total dividend announcements found: {len(cash_divs)}")

# Inspect first 5 dividend announcements
for a in cash_divs[:5]:
    aid = a.get("announcementId")
    cat = a.get("announcementCategory")
    dt = a.get("dateOfAnnouncement")
    print(f"\n==========================================")
    print(f"AnnouncementId: {aid} | Category: {cat} | Date: {dt}")
    r_detail = requests.post("https://www.cse.lk/api/getAnnouncementById", data={"announcementId": aid}, headers=headers)
    if r_detail.status_code == 200:
        d = r_detail.json()
        base = d.get("reqBaseAnnouncement", {})
        print("  dType:", base.get("dType"))
        for k, v in base.items():
            if any(term in k.lower() for term in ["dividend", "amount", "rate", "xd", "record", "pay", "share", "prop"]):
                print(f"    {k}: {v}")
        docs = d.get("reqAnnouncementDocs", [])
        if docs:
            print("  Docs:", [doc.get("path") for doc in docs])
