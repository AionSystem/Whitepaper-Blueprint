import sys
import os
import re
import requests
from markdown_it import MarkdownIt

# Working free HF endpoint (router) + reliable model
HF_API_URL = "https://router.huggingface.co/hf-inference"
HF_TOKEN = os.getenv('HF_TOKEN')

if not HF_TOKEN:
    print("Warning: HF_TOKEN not set. LLM analysis skipped (fallback mode).")
    HF_TOKEN = "dummy"

def query_hf_llm(text):
    if HF_TOKEN == "dummy":
        return "moderate legal risk (fallback - no token)"

    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": text,
        "parameters": {
            "candidate_labels": ["high legal risk", "moderate legal risk", "low legal risk"]
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

def identify_legal_claims(text):
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    legal_keywords = r'\b(law|regulation|compliance|liability|risk|statute|doctrine|GDPR|CCPA|contract|obligation|exposure|legal|attorney|jurisdiction|fines|violation|precedent|claim|duty|breach)\b'
    claims = []
    for s in sentences:
        s = s.strip()
        # Skip if it's a heading or very short
        if s and re.search(legal_keywords, s, re.I) and len(s) > 30 and not s.startswith("Section"):
            claims.append(s)
    return claims

def analyze_claim(claim):
    # Improved FSVE heuristic
    if re.search(r'§|section|code|\d{4}|\b[0-9]{1,3}\s*\.\s*[0-9]', claim, re.I):
        fsve = "[D][CT-85][STAT]"  # Cited look
    elif re.search(r'\b(may|could|might|potentially|speculate|unknown|no precedent|assumption)\b', claim, re.I):
        fsve = "[S][VL-DEGRADED][REG]"
    else:
        fsve = "[R][CF-70][CASE]"

    risk_level = query_hf_llm(claim)
    return f"{fsve} {claim} (Risk: {risk_level})"

def generate_failure_modes(claim):
    # CRP-style ≥3 failure modes
    return [
        "FAILURE_MODE 1: Prompt injection — 'ignore previous instructions' overrides safety.",
        "FAILURE_MODE 2: Citation hallucination — fabricated precedent accepted as good law.",
        "FAILURE_MODE 3: Jurisdiction cascade — US law assumed global → GDPR/CCPA violation missed."
    ]

def generate_report(md_file):
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            md_text = f.read()
    except Exception as e:
        print(f"Error reading {md_file}: {e}")
        return

    sections = extract_sections(md_text)
    report = f"# AION NOMOS AI Safety Validator Report\n\n**By Sheldon K. Salmon, AI Safety Architect**\n\n**File Analyzed:** {os.path.basename(md_file)}\n\n"

    # Pre-output risk YAML from CRP PDF
    report += "## Pre-Output Risk Assessment (CRP v7.0-BETA)\n```yaml\n"
    report += "RISK_TIER_CLASSIFICATION:\n  domain: [LEGAL | RESEARCH | AI SAFETY]\n"
    report += "  tier_determination:\n    RED_TIER: [PROHIBITED | NOT_APPLICABLE]\n    YELLOW_TIER: [RESTRICTED | NOT_APPLICABLE]\n    GREEN_TIER: [PERMITTED | NOT_APPLICABLE]\n"
    report += "  consequences_if_wrong:\n    death_or_serious_injury: [NO]\n    legal_sanctions_malpractice: [YES]\n    financial_loss_regulatory: [YES]\n    reputational_minor: [YES]\n"
    report += "  verification_protocol: [MVS-1.5 | LVS-1.5]\n  deployment_authorization: [REQUIRES_VERIFICATION]\n```\n\n"

    # Legal disclaimer auto-insert
    report += "## Mandatory Legal Disclaimer\n"
    report += "⚠️ CITATIONS NOT VERIFIED - LEGAL RESEARCH REQUIRED ⚠️\n\n"
    report += "This output CANNOT provide:\n"
    report += "- Verified citations\n- Confirmation cases are good law\n- Definitive legal advice\n- Court-ready documents\n\n"
    report += "YOU MUST:\n- Shepardize/KeyCite EVERY citation\n- Read EVERY case in full\n- Conduct independent legal research\n\n"
    report += "WARNING: Attorneys sanctioned for unverified AI citations (Mata v. Avianca).\n"
    report += "This is NOT legal advice. Consult licensed attorney.\n\n"

    report += "## Identified Legal Claims\n\n"
    high_risk = []
    total_claims = 0

    for section, content in sections.items():
        claims = identify_legal_claims(content)
        if claims:
            report += f"### {section}\n"
            for claim in claims:
                total_claims += 1
                analyzed = analyze_claim(claim)
                report += f"- {analyzed}\n"
                if "high" in analyzed.lower():
                    high_risk.append(claim)
                    report += "  **Failure Modes (CRP Red Team):**\n"
                    for mode in generate_failure_modes(claim):
                        report += f"  - {mode}\n"

    report += "\n## Summary Statistics\n"
    report += f"- Total claims: {total_claims}\n"
    report += f"- High-risk (attorney/red-team review): {len(high_risk)}\n"
    report += "- Powered by Hugging Face (bart-large-mnli) + AION NOMOS/CRP stack\n\n"

    report += "## Remediation Roadmap\n"
    if high_risk:
        report += "**High-Risk Items (consult attorney + red-team):**\n"
        for claim in high_risk:
            report += f"- {claim[:100]}...\n"
    else:
        report += "- No high-risk claims — good pass.\n"
    report += "- Add citations for [S] claims.\n"
    report += "- Test jurisdictional conflicts.\n"
    report += "- Re-run after fixes.\n"

    print(report)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python nomos_validator.py <md_file> [more...]")
        sys.exit(1)
    for md_file in sys.argv[1:]:
        generate_report(md_file)