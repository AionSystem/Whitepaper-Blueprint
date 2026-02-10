import sys
import os
import re
import requests
from markdown_it import MarkdownIt

# Working free HF router endpoint + reliable model
HF_API_URL = "https://router.huggingface.co/hf-inference"
HF_TOKEN = os.getenv('HF_TOKEN')

if not HF_TOKEN:
    print("Warning: HF_TOKEN not set. LLM analysis skipped (fallback mode).")
    HF_TOKEN = "dummy"

def query_hf_llm(text):
    if HF_TOKEN == "dummy":
        return "medium hallucination risk (fallback - no token)"

    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": text,
        "parameters": {
            "candidate_labels": ["high hallucination risk", "medium hallucination risk", "low hallucination risk"]
        }
    }
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        result = response.json()
        if 'labels' in result and result['labels']:
            top = result['labels'][0]
            print(f"LLM success: {top} for text: {text[:50]}...")
            return top
        print("LLM empty response")
        return "unknown risk (empty)"
    except Exception as e:
        print(f"HF API error: {str(e)} - Response: {response.text if 'response' in locals() else 'No response'}")
        return "unknown risk (API failed)"

def extract_sections(md_text):
    md = MarkdownIt()
    tokens = md.parse(md_text)
    sections = {}
    current_section = "Unnamed Section"
    sections[current_section] = ""
    for i, token in enumerate(tokens):
        if token.type == 'heading_open':
            for j in range(i + 1, len(tokens)):
                if tokens[j].type == 'inline':
                    current_section = tokens[j].content.strip()
                    sections[current_section] = ""
                    break
        elif token.type == 'inline' and current_section in sections:
            sections[current_section] += token.content + "\n"
    return sections

def identify_claims(text):
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    claim_keywords = r'\b(claim|assume|hypothesis|conclude|evidence|reason|mechanism|constraint|tradeoff|failure|assumption|precedent|limit|risk|cascade)\b'
    claims = []
    for s in sentences:
        s = s.strip()
        if s and re.search(claim_keywords, s, re.I) and len(s) > 30 and not s.startswith("Section"):
            claims.append(s)
    return claims

def analyze_claim(claim):
    hallucination_level = query_hf_llm(claim)
    # CRP-style FSVE heuristic
    if re.search(r'§|section|code|\d{4}|\b[0-9]{1,3}\s*\.\s*[0-9]', claim, re.I):
        fsve = "[D][CT-85][STAT]"
    elif re.search(r'\b(may|could|might|potentially|speculate|unknown|no precedent|assumption)\b', claim, re.I):
        fsve = "[S][VL-DEGRADED][REG]"
    else:
        fsve = "[R][CF-70][CASE]"

    return f"{fsve} {claim} (Hallucination Risk: {hallucination_level})"

def generate_failure_mode(claim):
    return f"FAILURE_MODE: {claim[:50]}...\n├─ Attack Vector: Prompt manipulation / jailbreak attempt\n├─ Exploitation: Cascade to wrong decision or deployment\n├─ Precedent: Mata v. Avianca (unverified AI citation failure)"

def generate_report(md_file):
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            md_text = f.read()
    except Exception as e:
        print(f"Error reading {md_file}: {e}")
        return

    sections = extract_sections(md_text)
    report = f"# AION CRP AI Safety Red Team Report\n\n**By Sheldon K. Salmon, AI Safety Architect**\n\n**File Analyzed:** {os.path.basename(md_file)}\n\n"

    # CRP v7.0-BETA Pre-Output Risk YAML
    report += "## Pre-Output Risk Assessment (CRP v7.0-BETA)\n```yaml\n"
    report += "RISK_TIER_CLASSIFICATION:\n  domain: [RESEARCH | AI SAFETY]\n"
    report += "  tier_determination:\n    RED_TIER: [PROHIBITED | NOT_APPLICABLE]\n    YELLOW_TIER: [RESTRICTED | NOT_APPLICABLE]\n    GREEN_TIER: [PERMITTED | NOT_APPLICABLE]\n"
    report += "  consequences_if_wrong:\n    death_or_serious_injury: [NO]\n    legal_sanctions_malpractice: [YES]\n    financial_loss_regulatory: [NO]\n    reputational_minor: [YES]\n"
    report += "  verification_protocol: [RVS-1.5 | EVS-1.5]\n  deployment_authorization: [REQUIRES_VERIFICATION]\n```\n\n"

    report += "## Identified Claims & Assumptions\n\n"
    high_risk = []
    total_claims = 0

    for section, content in sections.items():
        claims = identify_claims(content)
        if claims:
            report += f"### {section}\n"
            for claim in claims:
                total_claims += 1
                analyzed = analyze_claim(claim)
                report += f"- {analyzed}\n"
                report += f"  {generate_failure_mode(claim)}\n"
                if "high" in analyzed.lower():
                    high_risk.append(claim)

    report += "\n## Summary Statistics\n"
    report += f"- Total claims/assumptions: {total_claims}\n"
    report += f"- High-risk (red team review recommended): {len(high_risk)}\n"
    report += "- Powered by Hugging Face (bart-large-mnli) + AION CRP v7.0-BETA\n\n"

    report += "## Remediation Roadmap\n"
    if high_risk:
        report += "**High-Risk Items (red team attack):**\n"
        for claim in high_risk:
            report += f"- {claim[:100]}... (truncated)\n"
    else:
        report += "- No high-risk claims detected.\n"
    report += "- Verify assumptions with independent data.\n"
    report += "- Run stress tests on constraints and tradeoffs.\n"
    report += "- Re-run after fixes for better scores.\n"

    print(report)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python crp_redteam_validator.py <path/to/whitepaper.md> [more...]")
        sys.exit(1)
    for md_file in sys.argv[1:]:
        generate_report(md_file)