import sys
import os
import re
import requests
from markdown_it import MarkdownIt

HF_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
HF_TOKEN = os.getenv('HF_TOKEN')
if not HF_TOKEN:
    print("Warning: HF_TOKEN not set. LLM analysis skipped.")
    HF_TOKEN = "dummy"  # Fallback to avoid error

def query_hf_llm(text):
    if HF_TOKEN == "dummy":
        return "moderate legal risk"  # Fallback if no token

    payload = {
        "inputs": text,
        "parameters": {"candidate_labels": ["high legal risk", "moderate legal risk", "low legal risk"]}
    }
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(HF_API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        result = response.json()
        top_label = result['labels'][0]
        return top_label
    else:
        print(f"HF API error: {response.status_code}")
        return "unknown risk"

def extract_sections(md_text):
    md = MarkdownIt()
    tokens = md.parse(md_text)
    sections = {}
    current_section = ""
    for token in tokens:
        if token.type == 'heading_open':
            current_section = tokens[tokens.index(token) + 1].content
            sections[current_section] = ""
        elif token.type == 'inline' and current_section:
            sections[current_section] += token.content + "\n"
    return sections

def identify_legal_claims(text):
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    legal_keywords = r'\b(law|regulation|compliance|liability|risk|statute|doctrine|GDPR|CCPA|contract|obligation|exposure|legal|attorney|jurisdiction|fines|violation)\b'
    claims = [s.strip() for s in sentences if re.search(legal_keywords, s, re.I)]
    return claims

def analyze_claim(claim):
    risk_level = query_hf_llm(claim)
    fsve_tag = "[R][CT-80][CASE]" if "low" in risk_level else "[S][VL-DEGRADED][REG]" if "high" in risk_level else "[D][CF-70][STAT]"
    return f"{fsve_tag} {claim} (Risk: {risk_level})"

def generate_report(md_file):
    with open(md_file, 'r') as f:
        md_text = f.read()
    sections = extract_sections(md_text)
    report = "# NOMOS Legal Safety Report\n\n**File Analyzed:** " + md_file + "\n\n"
    report += "## Identified Legal Claims\n"
    high_risk = []
    for section, content in sections.items():
        claims = identify_legal_claims(content)
        for claim in claims:
            analyzed = analyze_claim(claim)
            report += f"- In '{section}': {analyzed}\n"
            if "high" in analyzed:
                high_risk.append(claim)
    report += "\n## Remediation Roadmap\n"
    if high_risk:
        report += "- **High-Risk Claims:** Consult attorney for these:\n"
        for claim in high_risk:
            report += f"  - {claim}\n"
    else:
        report += "- No high-risk claims detected. Review for compliance gaps.\n"
    report += "- Add citations for [S] speculations.\n"
    report += "- Test for jurisdictional conflicts (e.g., GDPR vs. CCPA).\n"
    print(report)

if __name__ == "__main__":
    for md_file in sys.argv[1:]:
        generate_report(md_file)