import sys
import markdown_it
import re

def extract_sections(md_text):
    md = markdown_it.MarkdownIt()
    tokens = md.parse(md_text)
    sections = {}
    current_section = ""
    for token in tokens:
        if token.type == 'heading_open':
            level = int(token.tag[1])
            if level == 1:
                current_section = next(t for t in tokens if t.type == 'inline').content
                sections[current_section] = ""
        elif token.type == 'paragraph_open' and current_section:
            content = next(t for t in tokens if t.type == 'inline').content
            sections[current_section] += content + "\n"
    return sections

def identify_legal_claims(text):
    # Simple regex for potential legal terms
    claims = re.findall(r'[A-Z]+ [a-z]+ (law|regulation|compliance|liability|risk|statute|doctrine)', text, re.I)
    return claims

def apply_fsve(claim):
    # Mock FSVE scoring
    score = "[R][CT-75][CASE]" if "doctrine" in claim else "[S][VL-DEGRADED][REG]"
    return f"{score} {claim}"

def generate_report(md_file):
    with open(md_file, 'r') as f:
        md_text = f.read()
    sections = extract_sections(md_text)
    report = "# NOMOS Legal Safety Report\n\n"
    report += "## Identified Legal Claims\n"
    for section, content in sections.items():
        claims = identify_legal_claims(content)
        for claim in claims:
            tagged = apply_fsve(claim)
            report += f"- In '{section}': {tagged}\n"
    report += "\n## Remediation Roadmap\n- Flag high-risk claims for attorney review\n- Add citations for [S] speculations"
    print(report)

if __name__ == "__main__":
    for md_file in sys.argv[1:]:
        generate_report(md_file)