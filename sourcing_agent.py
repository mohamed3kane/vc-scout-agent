import anthropic
import os
import requests
import json
from dotenv import load_dotenv
from scout_card import generate_scout_card

load_dotenv()

def fetch_product_hunt():
    url = "https://www.producthunt.com/feed"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    
    from xml.etree import ElementTree as ET
    root = ET.fromstring(response.content)
    
    # Atom namespace
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    
    products = []
    for entry in root.findall("atom:entry", ns)[:10]:
        title = entry.find("atom:title", ns).text or ""
        summary = entry.find("atom:summary", ns)
        description = summary.text if summary is not None else ""
        link = entry.find("atom:link", ns).get("href", "")
        products.append({
            "name": title,
            "description": description,
            "url": link
        })
    return products

def run_sourcing_agent():
    print("Fetching latest Product Hunt launches...\n")
    products = fetch_product_hunt()
    
    scout_cards = []
    for product in products:
        print(f"Analyzing: {product['name']}")
        card = generate_scout_card(product['name'], product['description'])
        scout_cards.append({
            "company": product['name'],
            "url": product['url'],
            "scout_card": card
        })
        print(card)
        print("-" * 60)
    
    with open("scout_cards.json", "w") as f:
        json.dump(scout_cards, f, indent=2)
    
    print(f"\nDone. {len(scout_cards)} scout cards saved to scout_cards.json")

if __name__ == "__main__":
    run_sourcing_agent()