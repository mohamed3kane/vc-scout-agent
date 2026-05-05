import json
import os
import csv
from datetime import datetime
from dotenv import load_dotenv
from analyst_agent import run_agentic_analyst, save_memo
from rag_analyst import run_rag_analyst

load_dotenv()

# 15 evaluation startups with known outcomes
EVAL_STARTUPS = [
    {"name": "Deel", "description": "Global payroll and compliance platform for remote teams. Handles contracts, payroll, and taxes for international employees in 150+ countries.", "known_outcome": "Success", "actual_verdict": "Invest"},
    {"name": "Pipe", "description": "Turns recurring revenue into upfront capital. SaaS companies can trade their annual recurring revenue for instant cash.", "known_outcome": "Success", "actual_verdict": "Invest"},
    {"name": "Brex", "description": "Corporate credit cards and financial software for startups. No personal guarantee required, instant approval based on funding.", "known_outcome": "Success", "actual_verdict": "Invest"},
    {"name": "Retool", "description": "Low-code platform for building internal tools. Drag and drop UI components connected to any database or API.", "known_outcome": "Success", "actual_verdict": "Invest"},
    {"name": "Causal", "description": "Financial modeling tool that replaces spreadsheets. Connects to data sources and builds models with natural language.", "known_outcome": "Success", "actual_verdict": "Watch"},
    {"name": "Pry Financials", "description": "Financial planning and forecasting tool for startups. Connects to QuickBooks, Stripe, and Gusto for real-time models.", "known_outcome": "Success", "actual_verdict": "Invest"},
    {"name": "Teal", "description": "Career development platform that helps people manage their job search, track applications, and build resumes.", "known_outcome": "Success", "actual_verdict": "Watch"},
    {"name": "Midnite", "description": "Esports betting platform for competitive gaming. Offers markets on major esports tournaments.", "known_outcome": "Success", "actual_verdict": "Watch"},
    {"name": "Lago", "description": "Open source billing and metering infrastructure for usage-based pricing. API-first, developer friendly.", "known_outcome": "Success", "actual_verdict": "Invest"},
    {"name": "Sweep", "description": "AI coding assistant that turns GitHub issues into pull requests automatically. Understands codebase context.", "known_outcome": "Success", "actual_verdict": "Invest"},
    {"name": "Stackup", "description": "Platform connecting developers to bounties and earn crypto rewards for completing coding tasks.", "known_outcome": "Stalled", "actual_verdict": "Pass"},
    {"name": "Doola", "description": "Business formation and compliance platform for international founders starting US companies.", "known_outcome": "Stalled", "actual_verdict": "Pass"},
    {"name": "Basedash", "description": "No-code database editor that lets non-technical teams edit databases directly without SQL.", "known_outcome": "Stalled", "actual_verdict": "Pass"},
    {"name": "Sequin", "description": "Syncs APIs like Salesforce and HubSpot to Postgres so developers can query them with SQL.", "known_outcome": "Stalled", "actual_verdict": "Watch"},
    {"name": "Kana", "description": "AI customer support automation for e-commerce brands. Handles returns, exchanges, and order tracking automatically.", "known_outcome": "Stalled", "actual_verdict": "Pass"},
]

def run_evaluation():
    os.makedirs("evaluation", exist_ok=True)
    results = []
    
    for i, startup in enumerate(EVAL_STARTUPS):
        print(f"\n{'='*60}")
        print(f"[{i+1}/15] Evaluating: {startup['name']}")
        print(f"Known outcome: {startup['known_outcome']}")
        print('='*60)
        
        scout_data = {
            "sector": "Unknown",
            "what_it_does": startup["description"],
            "investor_angle": "",
            "red_flags": ""
        }
        
        result = {
            "company": startup["name"],
            "description": startup["description"],
            "known_outcome": startup["known_outcome"],
            "actual_verdict": startup["actual_verdict"],
            "agentic_memo": "",
            "agentic_verdict": "",
            "rag_memo": "",
            "rag_verdict": "",
            "date": datetime.today().strftime("%Y-%m-%d")
        }
        
        # Run agentic
        try:
            print(f"\nRunning AGENTIC analyst...")
            agentic_memo = run_agentic_analyst(startup["name"], scout_data)
            result["agentic_memo"] = agentic_memo
            # Extract verdict
            for line in agentic_memo.split('\n'):
                if 'VERDICT:' in line.upper() and len(line) < 100:
                    verdict = line.split(':')[-1].strip().replace('**','').replace('##','').strip()
                    result["agentic_verdict"] = verdict
                    break
            save_memo(startup["name"], agentic_memo, memo_type="agentic_eval")
            print(f"Agentic verdict: {result['agentic_verdict']}")
        except Exception as e:
            print(f"Agentic error: {e}")
            result["agentic_memo"] = f"Error: {e}"

        # Run RAG
        try:
            print(f"\nRunning RAG analyst...")
            rag_memo = run_rag_analyst(startup["name"], scout_data)
            result["rag_memo"] = rag_memo
            for line in rag_memo.split('\n'):
                if 'VERDICT:' in line.upper() and len(line) < 100:
                    verdict = line.split(':')[-1].strip().replace('**','').replace('##','').strip()
                    result["rag_verdict"] = verdict
                    break
            save_memo(startup["name"], rag_memo, memo_type="rag_eval")
            print(f"RAG verdict: {result['rag_verdict']}")
        except Exception as e:
            print(f"RAG error: {e}")
            result["rag_memo"] = f"Error: {e}"

        results.append(result)
        
        # Save progress after each company
        with open("evaluation/results.json", "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nProgress saved ({i+1}/15)")

    # Export to CSV for scoring
    csv_path = "evaluation/evaluation_results.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "company", "known_outcome", "actual_verdict",
            "agentic_verdict", "rag_verdict",
            "agentic_verdict_match", "rag_verdict_match",
            "market_score_agentic", "market_score_rag",
            "competition_score_agentic", "competition_score_rag",
            "founder_score_agentic", "founder_score_rag",
            "traction_score_agentic", "traction_score_rag",
            "risk_score_agentic", "risk_score_rag",
            "total_agentic", "total_rag",
            "notes"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({
                "company": r["company"],
                "known_outcome": r["known_outcome"],
                "actual_verdict": r["actual_verdict"],
                "agentic_verdict": r["agentic_verdict"],
                "rag_verdict": r["rag_verdict"],
                "agentic_verdict_match": "",
                "rag_verdict_match": "",
                "market_score_agentic": "",
                "market_score_rag": "",
                "competition_score_agentic": "",
                "competition_score_rag": "",
                "founder_score_agentic": "",
                "founder_score_rag": "",
                "traction_score_agentic": "",
                "traction_score_rag": "",
                "risk_score_agentic": "",
                "risk_score_rag": "",
                "total_agentic": "",
                "total_rag": "",
                "notes": ""
            })
    
    print(f"\n{'='*60}")
    print(f"EVALUATION COMPLETE")
    print(f"Results saved to: evaluation/results.json")
    print(f"Scoring sheet saved to: {csv_path}")
    print(f"Open the CSV and fill in the score columns manually")
    print('='*60)

if __name__ == "__main__":
    run_evaluation()