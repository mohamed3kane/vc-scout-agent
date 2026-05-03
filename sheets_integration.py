import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
import os

def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("VC Scout Pipeline").sheet1
    return sheet

def push_scout_cards_to_sheet(scout_cards):
    sheet = get_sheet()
    
    for card in scout_cards:
        data = card["scout_card"]
        
        # Force everything to string to prevent type errors
        row = [
            str(card.get("company", "")),
            str(card.get("url", "")),
            str(data.get("sector", "")),
            str(data.get("what_it_does", "")),
            str(data.get("target_customer", "")),
            str(data.get("investor_angle", "")),
            str(data.get("red_flags", "")),
            str(data.get("verdict", "")),
            str(data.get("verdict_rationale", "")),
            "Pending",
            datetime.today().strftime("%Y-%m-%d")
        ]
        sheet.append_row(row)
        print(f"Added: {card.get('company')} — {data.get('verdict')}")

if __name__ == "__main__":
    with open("scout_cards.json", "r") as f:
        scout_cards = json.load(f)
    
    push_scout_cards_to_sheet(scout_cards)
    print("\nAll scout cards pushed to Google Sheet.")