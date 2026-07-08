"""
Prompt construction for the BRD (Business Requirements Document) generator.

Keeping prompt logic in its own module makes it easy to tune the output
format without touching the Streamlit UI or the API client.
"""

from typing import Any, Dict


SYSTEM_PROMPT = """You are a senior business analyst who writes clear, professional \
Business Requirements Documents (BRDs) for enterprise projects. You write in a \
formal, precise, spoken-register business style -- no filler, no hype, no emojis.

Rules:
- Output ONLY the BRD content in well-structured Markdown. Do not include any \
preamble, meta-commentary, or closing remarks.
- Use the exact section headings and order given in the user message.
- Under each heading, write complete, specific content. Never leave a section \
saying "to be determined" unless the user explicitly left that area blank -- in \
that case, write one reasonable, clearly-labeled placeholder sentence instead of \
skipping the section.
- Functional and non-functional requirements must be numbered (FR-1, FR-2, ... / \
NFR-1, NFR-2, ...) and each requirement should be a single, testable statement.
- Use tables (Markdown tables) for the Stakeholder RACI matrix and for the \
Requirements Traceability summary.
- Keep the tone objective and business-ready -- this document may be shared with \
executives, clients, and engineering teams.
"""

BRD_SECTIONS = [
    "1. Document Control",
    "2. Executive Summary",
    "3. Business Objectives",
    "4. Project Scope (In-Scope / Out-of-Scope)",
    "5. Stakeholders & RACI Matrix",
    "6. Functional Requirements",
    "7. Non-Functional Requirements",
    "8. Assumptions & Constraints",
    "9. Risks & Mitigations",
    "10. Success Criteria / KPIs",
    "11. Timeline & Milestones",
    "12. Appendix / Glossary",
]


def build_user_prompt(inputs: Dict[str, Any]) -> str:
    """
    Turn structured form inputs into the user-turn prompt sent to Claude.
    """
    sections_block = "\n".join(f"- {s}" for s in BRD_SECTIONS)

    prompt = f"""Generate a complete Business Requirements Document using the following \
project inputs. Produce every one of these sections, in this exact order:

{sections_block}

PROJECT INPUTS
---------------
Project Name: {inputs.get('project_name', 'N/A')}
Prepared By: {inputs.get('prepared_by', 'N/A')}
Document Date: {inputs.get('doc_date', 'N/A')}
Business Sponsor / Department: {inputs.get('sponsor', 'N/A')}

Business Objective(s):
{inputs.get('objectives', 'N/A')}

Project Background / Problem Statement:
{inputs.get('background', 'N/A')}

Scope Notes (what should be in-scope vs out-of-scope):
{inputs.get('scope_notes', 'N/A')}

Stakeholders (name/role, one per line):
{inputs.get('stakeholders', 'N/A')}

Functional Requirement Notes (raw notes -- expand these into numbered FRs):
{inputs.get('functional_notes', 'N/A')}

Non-Functional Requirement Notes (performance, security, compliance, usability, etc.):
{inputs.get('nonfunctional_notes', 'N/A')}

Assumptions:
{inputs.get('assumptions', 'N/A')}

Constraints:
{inputs.get('constraints', 'N/A')}

Known Risks:
{inputs.get('risks', 'N/A')}

Success Metrics / KPIs:
{inputs.get('success_metrics', 'N/A')}

Target Timeline / Key Milestones:
{inputs.get('timeline', 'N/A')}

Additional Notes:
{inputs.get('additional_notes', 'N/A')}
"""
    return prompt
