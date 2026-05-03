import anthropic
import os
import json
import numpy as np
from dotenv import load_dotenv
from tavily import TavilyClient
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

load_dotenv()

anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# ── Google Sheets ──────────────────────────────────────────
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

# ── Embeddings via Anthropic ───────────────────────────────
def get_embedding(text):
    response = anthropic_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=10,
        system="Return only the word OK.",
        messages=[{"role": "user", "content": text[:100]}]
    )
    # Since Anthropic doesn't expose embeddings directly,
    # we use a simple TF-based similarity instead
    return text

def cosine_similarity_text(query, doc):
    """Simple word overlap similarity as proxy for embeddings"""
    query_words = set(query.lower().split())
    doc_words = set(doc.lower().split())
    if not query_words or not doc_words:
        return 0
    intersection = query_words & doc_words
    return len(intersection) / (len(query_words) ** 0.5 * len(doc_words) ** 0.5)

# ── Corpus Builder ─────────────────────────────────────────
def build_corpus(company_name):
    print(f"  Building corpus for {company_name}...")

    queries = [
        f"{company_name} what does it do product description",
        f"{company_name} founders background team",
        f"{company_name} funding traction customers revenue",
        f"{company_name} competitors market landscape",
        f"{company_name} risks challenges problems"
    ]

    documents = []
    for query in queries:
        results = tavily_client.search(query, max_results=3)
        for r in results.get("results", []):
            documents.append({
                "title": r["title"],
                "content": r["content"],
                "query_origin": query
            })
        print(f"    Fetched: {query[:50]}...")

    print(f"  Corpus built — {len(documents)} documents")
    return documents

# ── RAG Retrieval ──────────────────────────────────────────
def retrieve(query, documents, top_k=4):
    """Retrieve most relevant documents for a query"""
    scored = []
    for doc in documents:
        score = cosine_similarity_text(query, doc["content"])
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]

# ── RAG Analyst ────────────────────────────────────────────
def run_rag_analyst(company_name, scout_card_data):
    print(f"\nRunning RAG analysis for {company_name}...")

    # Build corpus
    documents = build_corpus(company_name)

    # Retrieve relevant context for each memo section
    print("  Retrieving context for each memo section...")

    sections = {
        "market": f"market size growth rate industry dynamics for {company_name}",
        "competition": f"competitors alternatives differentiation for {company_name}",
        "founders": f"founders team background experience {company_name}",
        "traction": f"traction users revenue funding press coverage {company_name}",
        "risks": f"risks challenges problems weaknesses {company_name}"
    }

    retrieved = {}
    for section, query in sections.items():
        docs = retrieve(query, documents, top_k=3)
        retrieved[section] = "\n".join([
            f"[{d['title']}]: {d['content'][:400]}" for d in docs
        ])

    # Synthesize with Claude
    print("  Synthesizing memo from retrieved context...")

    prompt = f"""You are a VC analyst. Using ONLY the retrieved context below,
produce a structured investment memo for {company_name}.

Scout card:
{json.dumps(scout_card_data, indent=2)}

Retrieved context:
MARKET: {retrieved['market']}

COMPETITION: {retrieved['competition']}

FOUNDERS: {retrieved['founders']}

TRACTION: {retrieved['traction']}

RISKS: {retrieved['risks']}

Produce the memo with these exact sections:
MARKET: (size, growth, dynamics)
COMPETITION: (top 3 competitors, differentiation)
FOUNDER SIGNALS: (backgrounds, relevant experience)
TRACTION: (users, revenue, growth indicators, press)
RISKS: (top 3 structural risks)
VERDICT: (Invest / Watch / Pass)
RATIONALE: (2-3 sentence investment thesis or pass rationale)

Be specific. If context is missing for a section, say so explicitly."""

    response = anthropic_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text

def save_memo(company_name, memo, memo_type="rag"):
    os.makedirs("memos", exist_ok=True)
    filename = f"memos/{company_name.replace(' ', '_')}_{memo_type}.txt"
    with open(filename, "w") as f:
        f.write(f"INVESTMENT MEMO ({memo_type.upper()}): {company_name}\n")
        f.write(f"Generated: {datetime.today().strftime('%Y-%m-%d')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(memo)
    print(f"  Memo saved to {filename}")

if __name__ == "__main__":
    approved = get_approved_companies()

    if not approved:
        print("No approved companies. Set Status to 'Approve' in your Google Sheet.")
    else:
        for company in approved:
            name = company.get("Company", "Unknown")
            scout_data = {
                "sector": company.get("Sector", ""),
                "what_it_does": company.get("What It Does", ""),
                "investor_angle": company.get("Investor Angle", ""),
                "red_flags": company.get("Red Flags", "")
            }

            memo = run_rag_analyst(name, scout_data)
            save_memo(name, memo, memo_type="rag")

            print(f"\n{'='*60}")
            print(memo)