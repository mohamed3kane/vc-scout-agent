import anthropic
import os
import json
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def generate_scout_card(company_name, description, thesis=""):
    thesis_context = f"\n\nInvestment thesis to evaluate against:\n{thesis}" if thesis else ""

    prompt = f"""You are a VC scout evaluating early-stage startups.{thesis_context}

Here is a newly launched product:
Company: {company_name}
Description: {description}

Return a JSON object with exactly these fields, no other text:
{{
  "sector": "one of: SaaS / Fintech / DevTools / Healthcare / Consumer / AI Infrastructure / Other",
  "what_it_does": "one sentence plain English",
  "target_customer": "who pays for this",
  "investor_angle": "why an early-stage investor might care — evaluate against the investment thesis if provided",
  "red_flags": "one honest concern",
  "verdict": "Interesting / Watch / Pass",
  "verdict_rationale": "one sentence rationale — reference the investment thesis if provided"
}}

Return only valid JSON, no markdown, no explanation."""

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "sector": "Unknown",
            "what_it_does": "Could not parse",
            "target_customer": "Unknown",
            "investor_angle": "Unknown",
            "red_flags": "Parsing error",
            "verdict": "Pass",
            "verdict_rationale": "Insufficient data to evaluate"
        }

if __name__ == "__main__":
    result = generate_scout_card(
        company_name="Deel",
        description="Deel helps companies hire anyone, anywhere. It handles contracts, payroll, and compliance for international employees and contractors in 150+ countries."
    )
    print(json.dumps(result, indent=2))