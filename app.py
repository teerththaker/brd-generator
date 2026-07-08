"""
BRD Generator -- Streamlit app.

Collects structured project inputs, sends them to Claude to draft a full
Business Requirements Document, and lets the user preview, refine, and
download the result as Markdown, DOCX, or PDF.

Run locally:
    streamlit run app.py

Deploy on Streamlit Community Cloud:
    Push this repo to GitHub, create a new app pointing at app.py, and add
    ANTHROPIC_API_KEY to the app's Secrets (see README.md).
"""

import os
from datetime import date

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# On Streamlit Community Cloud, values live in st.secrets, not the process
# environment. backend.config reads os.environ at import time, so copy any
# of these over first -- this keeps local (.env) and cloud (Secrets)
# configuration behaving identically.
for _key in ("ANTHROPIC_API_KEY", "LLM_MODEL", "LLM_EFFORT", "LLM_MAX_TOKENS"):
    if _key not in os.environ:
        try:
            if _key in st.secrets:
                os.environ[_key] = str(st.secrets[_key])
        except Exception:
            pass  # no secrets.toml present (e.g. local run without one) -- fine

from backend import config
from backend.claude_client import BRDGenerationError, generate_brd, refine_brd
from backend.document_export import markdown_to_docx, markdown_to_pdf

st.set_page_config(
    page_title="BRD Generator",
    page_icon="\U0001F4C4",
    layout="wide",
)

MODEL_OPTIONS = {
    f"Environment default ({config.LLM_MODEL})": config.LLM_MODEL,
    "Claude Sonnet 5 (fast & high quality)": "claude-sonnet-5",
    "Claude Opus 4.8 (highest quality, slower/costlier)": "claude-opus-4-8",
    "Claude Haiku 4.5 (fastest, most economical)": "claude-haiku-4-5-20251001",
}


def get_api_key() -> str:
    """Resolve the API key from, in order: sidebar input, Streamlit secrets, env var."""
    if st.session_state.get("api_key_input"):
        return st.session_state["api_key_input"]
    try:
        if "ANTHROPIC_API_KEY" in st.secrets:
            return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY", "")


def init_session_state():
    defaults = {
        "brd_markdown": "",
        "project_name": "",
        "generating": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()

# ---------------------------------------------------------------- Sidebar --
with st.sidebar:
    st.title("\U0001F4C4 BRD Generator")
    st.caption("AI-drafted Business Requirements Documents, powered by Claude.")

    st.subheader("API Configuration")
    st.text_input(
        "Anthropic API Key",
        type="password",
        key="api_key_input",
        placeholder="sk-ant-...",
        help="Not stored anywhere. You can also set ANTHROPIC_API_KEY as an "
        "environment variable or Streamlit secret to skip this field.",
    )

    model_label = st.selectbox("Model", list(MODEL_OPTIONS.keys()), index=0)
    selected_model = MODEL_OPTIONS[model_label]

    st.divider()
    st.caption(
        "Built with Streamlit + the Anthropic Claude API. "
        "See README.md for setup and deployment instructions."
    )

# ------------------------------------------------------------------ Form --
st.header("Project Inputs")
st.caption("Fill in what you know -- Claude will expand sparse notes into full BRD sections.")

with st.form("brd_form"):
    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("Project Name*", placeholder="e.g. Customer Portal Revamp")
        prepared_by = st.text_input("Prepared By", placeholder="Your name / team")
        sponsor = st.text_input("Business Sponsor / Department", placeholder="e.g. VP of Operations")
    with col2:
        doc_date = st.date_input("Document Date", value=date.today())
        stakeholders = st.text_area(
            "Stakeholders (one per line: name -- role)",
            placeholder="Jane Doe -- Project Sponsor\nJohn Smith -- Engineering Lead",
            height=100,
        )

    objectives = st.text_area(
        "Business Objective(s)*",
        placeholder="What business outcome should this project achieve?",
        height=90,
    )
    background = st.text_area(
        "Project Background / Problem Statement",
        placeholder="What problem exists today? Why now?",
        height=90,
    )
    scope_notes = st.text_area(
        "Scope Notes (in-scope vs out-of-scope)",
        placeholder="What is definitely included? What is explicitly excluded?",
        height=90,
    )

    col3, col4 = st.columns(2)
    with col3:
        functional_notes = st.text_area(
            "Functional Requirement Notes*",
            placeholder="Raw notes -- Claude will expand these into numbered FR-1, FR-2, ...",
            height=140,
        )
        assumptions = st.text_area("Assumptions", height=90)
        risks = st.text_area("Known Risks", height=90)
    with col4:
        nonfunctional_notes = st.text_area(
            "Non-Functional Requirement Notes",
            placeholder="Performance, security, compliance, usability, availability...",
            height=140,
        )
        constraints = st.text_area("Constraints", height=90)
        success_metrics = st.text_area("Success Metrics / KPIs", height=90)

    timeline = st.text_area("Target Timeline / Key Milestones", height=70)
    additional_notes = st.text_area("Additional Notes", height=70)

    submitted = st.form_submit_button("Generate BRD", use_container_width=True, type="primary")

if submitted:
    api_key = get_api_key()
    missing_required = not project_name or not objectives or not functional_notes

    if missing_required:
        st.error("Please fill in at least Project Name, Business Objective(s), and Functional Requirement Notes.")
    elif not api_key:
        st.error("Please enter your Anthropic API key in the sidebar (or set ANTHROPIC_API_KEY).")
    else:
        inputs = {
            "project_name": project_name,
            "prepared_by": prepared_by,
            "doc_date": doc_date.isoformat(),
            "sponsor": sponsor,
            "objectives": objectives,
            "background": background,
            "scope_notes": scope_notes,
            "stakeholders": stakeholders,
            "functional_notes": functional_notes,
            "nonfunctional_notes": nonfunctional_notes,
            "assumptions": assumptions,
            "constraints": constraints,
            "risks": risks,
            "success_metrics": success_metrics,
            "timeline": timeline,
            "additional_notes": additional_notes,
        }

        with st.spinner("Drafting your BRD with Claude... this can take up to a minute."):
            try:
                result = generate_brd(inputs, api_key=api_key, model=selected_model)
                st.session_state["brd_markdown"] = result
                st.session_state["project_name"] = project_name or "BRD"
                st.success("BRD generated below.")
            except BRDGenerationError as exc:
                st.error(str(exc))

# --------------------------------------------------------- Output / edit --
if st.session_state["brd_markdown"]:
    st.divider()
    st.header("Generated BRD")

    preview_tab, refine_tab = st.tabs(["Preview & Download", "Refine with Claude"])

    with preview_tab:
        st.markdown(st.session_state["brd_markdown"])

        st.divider()
        st.subheader("Download")
        file_stub = (st.session_state["project_name"] or "BRD").strip().replace(" ", "_")

        dcol1, dcol2, dcol3 = st.columns(3)
        with dcol1:
            st.download_button(
                "\u2b07\ufe0f Download Markdown (.md)",
                data=st.session_state["brd_markdown"],
                file_name=f"{file_stub}_BRD.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with dcol2:
            docx_bytes = markdown_to_docx(
                st.session_state["brd_markdown"],
                title=f"{st.session_state['project_name']} -- Business Requirements Document",
            )
            st.download_button(
                "\u2b07\ufe0f Download Word (.docx)",
                data=docx_bytes,
                file_name=f"{file_stub}_BRD.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        with dcol3:
            pdf_bytes = markdown_to_pdf(
                st.session_state["brd_markdown"],
                title=f"{st.session_state['project_name']} -- Business Requirements Document",
            )
            st.download_button(
                "\u2b07\ufe0f Download PDF (.pdf)",
                data=pdf_bytes,
                file_name=f"{file_stub}_BRD.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    with refine_tab:
        st.caption(
            "Ask Claude to revise the document -- e.g. \"expand the risks section\", "
            "\"make the tone more formal\", \"add two more functional requirements about reporting\"."
        )
        instruction = st.text_area("Revision instruction", height=80, key="refine_instruction")
        if st.button("Apply Revision", type="primary"):
            api_key = get_api_key()
            if not instruction.strip():
                st.warning("Enter an instruction first.")
            elif not api_key:
                st.error("Please enter your Anthropic API key in the sidebar.")
            else:
                with st.spinner("Revising with Claude..."):
                    try:
                        revised = refine_brd(
                            st.session_state["brd_markdown"],
                            instruction,
                            api_key=api_key,
                            model=selected_model,
                        )
                        st.session_state["brd_markdown"] = revised
                        st.success("Document revised. Switch to the Preview tab to see changes.")
                        st.rerun()
                    except BRDGenerationError as exc:
                        st.error(str(exc))
else:
    st.info("Fill in the project inputs above and click **Generate BRD** to get started.")
