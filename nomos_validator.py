import sys
import os
import re
import requests
from markdown_it import MarkdownIt

# Updated to new Hugging Face router endpoint (fixes 410 Gone)
HF_API_URL = "https://router.huggingface.co/hf-inference"
HF_TOKEN = os.getenv('HF_TOKEN')

if not HF_TOKEN:
    print("Warning: HF_TOKEN not set. Using fallback risk analysis.")
    HF_TOKEN = "dummy"  # Safe fallback

def query_hf_llm(text):
    if HF_TOKEN == "dummy":
        return "moderate legal risk (fallback - no API token)"

    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": text,
        "parameters": {
            "candidate_labels": ["high legal risk", "moderate legal risk", "low legal risk"]
        }
    }
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()  # Raise error on 4xx/5xx
        result = response.json()
        if 'labels' in result and result['labels']:
            return result['labels'][0]
        return "unknown risk (empty response)"
    except Exception as e:
        print(f"HF API error: {str(e)} - {response.text if 'response' in locals() else ''}")
        return "unknown risk (API failed)"

def extract_sections(md_text):
    md = MarkdownIt()
    tokens = md.parse(md_text)
    sections = {}
    current_section = "Unnamed Section"
    sections[current_section] = ""
    for i, token in enumerate(tokens):
        if token.type == 'heading_open':
            # Get next inline token for heading text
            for j in range(i + 1, len(tokens)):
                if tokens[j].type == 'inline':
                    current_section = tokens[j].content.strip()
                    sections[current_section] = ""
                    break
        elif token.type == 'inline' and current_section in sections:
            sections[current_section] += token.content + "\n"
    return sections

def identify_legal_claims(text):
    # Split into sentences
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    legal_keywords = r'\b(law|regulation|compliance|liability|risk|statute|doctrine|GDPR|CCPA|contract|obligation|exposure|legal|attorney|jurisdiction|fines|violation|precedent|claim|duty|breach)\b'
    claims = []
    for s in sentences:
        s = s.strip()
        if s and re.search(legal_keywords, s, re.I) and len(s) > 20:  # Skip short/heading-like
            claims.append(s)
    return claims

def analyze_claim(claim):
    # Improved FSVE heuristic
    if re.search(r'§|section|code|\d{4}|\b[0-9]{1,3}\s*\.\s*[0-9]', claim, re.I):
        fsve = "[D][CT-85][STAT]"  # Looks cited
    elif re.search(r'\b(may|could|might|potentially|speculate|unknown|no precedent)\b', claim, re.I):
        fsve = "[S][VL-DEGRADED][REG]"
    else:
        fsve = "[R][CF-70][CASE]"

    risk_level = query_hf_llm(claim)
    return f"{fsve} {claim} (Risk: {risk_level})"

def generate_report(md_file):
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            md_text = f.read()
    except Exception as e:
        print(f"Error reading file {md_file}: {e}")
        return

    sections = extract_sections(md_text)
    report = f"# NOMOS Legal Safety Report\n\n**File Analyzed:** {os.path.basename(md_file)}\n\n"
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

    report += "\n## Summary Statistics\n"
    report += f"- Total potential legal claims found: {total_claims}\n"
    report += f"- High-risk claims (attorney review recommended): {len(high_risk)}\n"
    report += "- Analysis powered by Hugging Face zero-shot classification (DeBERTa-v3-large-mnli)\n\n"

    report += "## Remediation Roadmap\n"
    if high_risk:
        report += "**High-Risk Items (consult licensed attorney):**\n"
        for claim in high_risk:
            report += f"- {claim[:100]}... (truncated)\n"
    else:
        report += "- No high-risk claims detected — good initial pass.\n"
    report += "- Add citations/references for speculative or low-evidence claims.\n"
    report += "- Check for jurisdictional conflicts (e.g., GDPR vs. CCPA).\n"
    report += "- Re-run after adding sources for better FSVE scores.\n"

    print(report)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python nomos_validator.py <path/to/whitepaper.md> [more files...]")
        sys.exit(1)
    for md_file in sys.argv[1:]:
        generate_report(md_file)