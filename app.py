from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
import json
import os
from datetime import datetime
from dotenv import load_dotenv

from scout_card import generate_scout_card
from analyst_agent import run_agentic_analyst, save_memo
from rag_analyst import run_rag_analyst

load_dotenv()

app = Flask(__name__, static_folder="static")
CORS(app)

import gspread
from google.oauth2.service_account import Credentials

def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)
    return client.open("VC Scout Pipeline").sheet1

def get_existing_companies():
    try:
        sheet = get_sheet()
        rows = sheet.get_all_records()
        return set(r.get("Company", "").strip().lower() for r in rows)
    except Exception:
        return set()

def save_to_sheet(company):
    try:
        sheet = get_sheet()
        sheet.append_row([
            company.get("company", ""),
            company.get("url", ""),
            company.get("sector", ""),
            company.get("what_it_does", ""),
            company.get("target_customer", ""),
            company.get("investor_angle", ""),
            company.get("red_flags", ""),
            company.get("verdict", ""),
            company.get("verdict_rationale", ""),
            company.get("status", "Pending"),
            datetime.today().strftime("%Y-%m-%d"),
            ""  # memo column, empty initially
        ])
    except Exception as e:
        print(f"Sheet save error: {e}")

def update_status_in_sheet(company_name, status):
    try:
        sheet = get_sheet()
        rows = sheet.get_all_records()
        for i, row in enumerate(rows):
            if row.get("Company") == company_name:
                sheet.update_cell(i + 2, 10, status)
                break
    except Exception as e:
        print(f"Sheet update error: {e}")

def save_memo_to_sheet(company_name, memo, memo_type):
    try:
        sheet = get_sheet()
        rows = sheet.get_all_records()
        for i, row in enumerate(rows):
            if row.get("Company") == company_name:
                sheet.update_cell(i + 2, 12, f"[{memo_type.upper()}]\n{memo}")
                break
    except Exception as e:
        print(f"Sheet memo save error: {e}")

@app.route("/")
def index():
    with open(os.path.join(app.static_folder, "index.html"), "r") as f:
        content = f.read()
    return Response(content, mimetype="text/html")

@app.route("/api/fetch-startups", methods=["GET"])
def fetch_startups():
    try:
        import requests
        from xml.etree import ElementTree as ET

        thesis = request.args.get("thesis", "")

        url = "https://www.producthunt.com/feed"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(response.content)

        existing = get_existing_companies()
        startups = []

        for entry in root.findall("atom:entry", ns)[:10]:
            title = entry.find("atom:title", ns).text or ""
            summary = entry.find("atom:summary", ns)
            description = summary.text if summary is not None else ""
            link = entry.find("atom:link", ns).get("href", "")

            if title.strip().lower() in existing:
                print(f"Skipping (already analyzed): {title}")
                continue

            print(f"Generating scout card for: {title}")
            card = generate_scout_card(title, description, thesis=thesis)

            startup = {
                "company": title,
                "url": link,
                "sector": card.get("sector", ""),
                "what_it_does": card.get("what_it_does", ""),
                "target_customer": card.get("target_customer", ""),
                "investor_angle": card.get("investor_angle", ""),
                "red_flags": card.get("red_flags", ""),
                "verdict": card.get("verdict", ""),
                "verdict_rationale": card.get("verdict_rationale", ""),
                "status": "Pending"
            }

            startups.append(startup)
            save_to_sheet(startup)

        return jsonify({"success": True, "startups": startups})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/update-status", methods=["POST"])
def update_status():
    try:
        data = request.json
        company_name = data.get("company")
        status = data.get("status")
        update_status_in_sheet(company_name, status)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/generate-memo", methods=["POST"])
def generate_memo():
    try:
        data = request.json
        company = data.get("company")
        mode = data.get("mode", "agentic")
        thesis = data.get("thesis", "")

        scout_data = {
            "sector": data.get("sector", ""),
            "what_it_does": data.get("what_it_does", ""),
            "investor_angle": data.get("investor_angle", ""),
            "red_flags": data.get("red_flags", "")
        }

        if mode == "agentic":
            memo = run_agentic_analyst(company, scout_data, thesis=thesis)
        else:
            memo = run_rag_analyst(company, scout_data)

        save_memo(company, memo, memo_type=mode)
        save_memo_to_sheet(company, memo, memo_type=mode)

        return jsonify({"success": True, "memo": memo, "mode": mode})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/history", methods=["GET"])
def get_history():
    try:
        sheet = get_sheet()
        rows = sheet.get_all_records()
        return jsonify({"success": True, "history": rows})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    os.makedirs("static", exist_ok=True)
    os.makedirs("memos", exist_ok=True)
    app.run(debug=True, port=5000)