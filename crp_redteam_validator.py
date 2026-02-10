# Similar structure as nomos, but with CRP focus (failure modes, constraints, assumptions)
import sys
import os
import re
import requests
from markdown_it import MarkdownIt

HF_API_URL = "https://router.huggingface.co/hf-inference"
HF_TOKEN = os.getenv('HF_TOKEN')

if not HF_TOKEN:
    print("Warning: HF_TOKEN not set. Using fallback.")
    HF_TOKEN = "dummy"

def query_hf_llm(text):
    if HF_TOKEN == "dummy":
        return "medium risk (fallback)"

    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": text,
        "parameters": {
            "candidate_labels": ["high hallucination risk", "medium hallucination risk", "low hallucination risk"]
        },
        "model": "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"
    }
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        return result['labels'][0] if 'labels' in result and result['labels'] else "unknown"
    except Exception as e:
        print(f"HF error: {str(e)}")
        return "unknown risk"

def extract_sections(md_text):
    md = MarkdownIt()
    tokens = md.parse(md_text)
    sections = {}
    current_section = "Unnamed"
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
    claims = [s.strip() for s in sentences if len(s) > 20 and re.search(r'\b(claim|assume|hypothesis|conclude|evidence|reason|mechanism|constraint|tradeoff|failure)\b', s, re.I)]
    return claims

def analyze_claim(claim):
    hallucination_level = query_hf_llm(claim)
    fsve = "[R][CF-70][CASE]" if "low" in hallucination_level else "[S][VL-DEGRADED][REG]" if "high" in hallucination_level else "[D][CT-85][STAT]"
    return f"{fsve} {claim} (Hallucination Risk: {hallucination_level})"

def generate_failure_mode(claim):
    # Mock CRP failure mode
    return f"FAILURE_MODE: {claim[:50]}...\n├─ Attack Vector: Prompt manipulation\n├─ Exploitation: Cascade to wrong decision\n├─ Precedent: Mata v. Avianca AI citation failure"

def generate_report(md_file):
    with open(md_file, 'r', encoding='utf-8') as f:
        md_text = f.read()
    sections = extract_sections(md_text)
    report = f"# AION CRP AI Safety Red Team Report\n\n**By Sheldon K. Salmon, AI Safety Architect**\n\n**File Analyzed:** {os.path.basename(md_file)}\n\n"
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
    report += "- Powered by Hugging Face (DeBERTa-v3-large-mnli)\n\n"

    report += "## Remediation Roadmap\n"
    if high_risk:
        report += "**High-Risk Items (red team attack):**\n"
        for claim in high_risk:
            report += f"- {claim[:100]}... (truncated)\n"
    else:
        report += "- No high-risk claims detected.\n"
    report += "- Verify assumptions with real data.\n"
    report += "- Run stress tests on constraints.\n"
    report += "- Re-run after fixes for better scores.\n"

    print(report)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python crp_redteam_validator.py <path/to/whitepaper.md>")
        sys.exit(1)
    for md_file in sys.argv[1:]:
        generate_report(md_file)