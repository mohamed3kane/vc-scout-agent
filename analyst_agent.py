import anthropic
import os
import json
from dotenv import load_dotenv
from tavily import TavilyClient
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

load_dotenv()

anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)
    return client.open("VC Scout Pipeline").sheet1

def get_approved_companies():
    sheet = get_sheet()
    rows = sheet.get_all_records()
    approved = [r for r in rows if r.get("Status", "").strip().lower() == "approve"]
    print(f"Found {len(approved)} approved companies")
    return approved

tools = [
    {
        "name": "web_search",
        "description": "Search the web for information about a company, market, or competitors",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                }
            },
            "required": ["query"]
        }
    }
]

def run_agentic_analyst(company_name, scout_card_data, thesis=""):
    print(f"\nResearching {company_name}...")

    thesis_context = f"\n\nInvestment thesis to evaluate against:\n{thesis}" if thesis else ""

    messages = [
        {
            "role": "user",
            "content": f"""You are a VC analyst producing an investment memo for {company_name}.{thesis_context}

Here is what our scout found:
{json.dumps(scout_card_data, indent=2)}

Use web search to research this company. You have a maximum of 10 searches — use them wisely.
Focus on: what they do, market size, competitors, founder backgrounds, traction, key risks.

Once you have enough information, produce a structured investment memo with these exact sections:

INVESTMENT MEMO: {company_name}

## MARKET
(size, growth, dynamics)

## COMPETITION
(top 3 competitors, differentiation)

## FOUNDER SIGNALS
(backgrounds, relevant experience)

## TRACTION
(users, revenue, growth indicators, press)

## RISKS
(top 3 structural risks)

## VERDICT
(Invest / Watch / Pass)

## RATIONALE
(2-3 sentence investment thesis or pass rationale)

## SCORE
Confidence: X/10
Suggested Check Size: $XXK-$XXK
Follow-up Priority: High / Medium / Low
"""
        }
    ]

    search_count = 0
    max_searches = 10

    while True:
        response = anthropic_client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "tool_use" and search_count < max_searches:
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            tool_results = []

            for tool_use in tool_uses:
                query = tool_use.input["query"]
                search_count += 1
                print(f"  Search {search_count}: {query}")

                results = tavily_client.search(query, max_results=3)
                search_text = "\n".join([
                    f"- {r['title']}: {r['content'][:300]}"
                    for r in results.get("results", [])
                ])

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": search_text
                })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            if search_count >= max_searches:
                print(f"  Search limit reached — forcing memo compilation")
                messages.append({
                    "role": "user",
                    "content": "Search limit reached. Compile your investment memo now with the information gathered."
                })

        else:
            memo = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            if "INVESTMENT MEMO" in memo:
                memo = memo[memo.index("INVESTMENT MEMO"):]
            elif "## MARKET" in memo:
                memo = memo[memo.index("## MARKET"):]
            print(f"  Done — {search_count} searches performed")
            return memo

def save_memo(company_name, memo, memo_type="agentic"):
    os.makedirs("memos", exist_ok=True)
    filename = f"memos/{company_name.replace(' ', '_')}_{memo_type}.txt"
    with open(filename, "w") as f:
        f.write(f"INVESTMENT MEMO ({memo_type.upper()}): {company_name}\n")
        f.write(f"Generated: {datetime.today().strftime('%Y-%m-%d')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(memo)
    print(f"  Memo saved to {filename}")
    return filename

if __name__ == "__main__":
    approved = get_approved_companies()
    if not approved:
        print("No approved companies found.")
    else:
        for company in approved:
            name = company.get("Company", "Unknown")
            scout_data = {
                "sector": company.get("Sector", ""),
                "what_it_does": company.get("What It Does", ""),
                "investor_angle": company.get("Investor Angle", ""),
                "red_flags": company.get("Red Flags", "")
            }
            memo = run_agentic_analyst(name, scout_data)
            save_memo(name, memo, memo_type="agentic")
            print(f"\n{'='*60}")
            print(memo)