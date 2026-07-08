# BRD Generator

An AI-powered Business Requirements Document (BRD) generator. Fill in a short
form of project inputs, and [Claude](https://www.anthropic.com) drafts a
complete, professionally structured BRD -- covering scope, stakeholders,
functional/non-functional requirements, risks, KPIs, and more -- which you
can preview, refine conversationally, and export as **Markdown**, **Word
(.docx)**, or **PDF**.

Built with [Streamlit](https://streamlit.io) and the
[Anthropic Claude API](https://docs.claude.com).

---

## Features

- Structured intake form for all standard BRD inputs (objectives, scope,
  stakeholders, functional/non-functional requirements, risks, KPIs, timeline)
- Claude expands sparse notes into a full, numbered, business-ready document
- In-app "Refine with Claude" tab -- ask for revisions in plain English
  ("expand the risks section", "add two more functional requirements")
- One-click export to `.md`, `.docx`, and `.pdf`
- Clean separation between UI (`app.py`) and backend logic (`backend/`)

## Project Structure

```
brd-generator/
├── app.py                        # Streamlit frontend (UI + orchestration)
├── backend/
│   ├── __init__.py
│   ├── claude_client.py          # Anthropic API wrapper (generate / refine)
│   ├── brd_prompts.py            # System + user prompt templates
│   └── document_export.py        # Markdown -> DOCX / PDF converters
├── .streamlit/
│   ├── config.toml               # App theme
│   └── secrets.toml.example      # Template for Streamlit Cloud secrets
├── requirements.txt
├── .env.example                  # Template for local environment variables
├── .gitignore
└── README.md
```

## Getting an API Key

1. Sign in to the [Claude Platform Console](https://platform.claude.com).
2. Open **API Keys** and create a new key.
3. Copy it once -- the console won't show it again.

## Run Locally

```bash
git clone https://github.com/<your-username>/brd-generator.git
cd brd-generator

python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# edit .env and paste your ANTHROPIC_API_KEY

streamlit run app.py
```

The app opens at `http://localhost:8501`. You can also skip `.env` entirely
and paste your API key directly into the sidebar field at runtime -- it is
only held in the Streamlit session and never written to disk.

## Deploying on Streamlit Community Cloud

1. Push this project to a **public or private GitHub repo**.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with
   GitHub.
3. Click **New app**, select this repo, branch, and set the main file path
   to `app.py`.
4. Before (or after) deploying, open **App settings -> Secrets** and add:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-your-key-here"
   ```
   This mirrors `.streamlit/secrets.toml.example` -- the app reads
   `st.secrets["ANTHROPIC_API_KEY"]` automatically so users don't have to
   paste a key in themselves (though the sidebar field still works as an
   override).
5. Deploy. Streamlit Cloud installs `requirements.txt` automatically.

> **Note:** Do not commit a real `secrets.toml` or `.env` file -- both are
> already excluded via `.gitignore`.

## Changing the Model

The default model is `claude-sonnet-5`, a strong balance of quality, speed,
and cost for long-form structured documents. You can switch models from the
sidebar dropdown in the app (Sonnet 5 / Opus 4.8 / Haiku 4.5), or change the
default in `backend/claude_client.py` (`DEFAULT_MODEL`). See the
[models overview](https://docs.claude.com/en/docs/about-claude/models/overview)
for current model IDs and pricing.

## How It Works

1. `app.py` collects form inputs and calls `backend.claude_client.generate_brd()`.
2. `backend/brd_prompts.py` builds a system prompt (BRD-writing rules and
   formatting constraints) and a user prompt (your structured inputs).
3. Claude returns a complete BRD in Markdown, rendered live in the app.
4. `backend/document_export.py` converts that Markdown into `.docx` (via
   `python-docx`) and `.pdf` (via `fpdf2`) on demand, entirely in memory --
   no files are written to disk.
5. The "Refine with Claude" tab sends the current document back to Claude
   along with a follow-up instruction and replaces it with the revised
   version.

## Extending

- **New export formats:** add a function to `backend/document_export.py`
  and a matching `st.download_button` in `app.py`.
- **New BRD sections:** edit `BRD_SECTIONS` and the system prompt in
  `backend/brd_prompts.py`.
- **Multi-document history:** persist generated BRDs to a database or file
  store keyed by session, since Streamlit session state resets per browser
  session.

## License

MIT -- use freely for your own projects.
