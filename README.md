# StudyAI — AI Study Assistant

StudyAI turns your own course materials into **source-grounded** study sets —
quizzes, flashcards, explanations, and open-response Q&A. Upload a PDF, Word
document, image, or pasted notes; the app extracts the text, finds the passages
most relevant to your topic, and uses a language model to generate study content
where **every answer is traced back to the snippet it came from**.

Built for the SDEV378 Applied AI final project: a working proof of concept with
three ML components cooperating end to end (extraction → retrieval →
generation), plus an optional fourth (automatic topic and difficulty tagging).

**Team:** Maxwell Maslov, Huma Khomidov

---

## Features

- **Multiple input types** — PDF, Word (`.docx`), images (`.png/.jpg/...`), `.txt` / `.md` / `.csv`, or pasted text.
- **Four study modes** — multiple-choice **quiz**, **flashcards**, **explanations**, and open-response **Q&A**.
- **Grounded answers** — the model may only use passages retrieved from *your* material, and each item links to its source snippet.
- **Automatic tagging** — detects topics and a suggested difficulty to seed retrieval.
- **Graceful degradation** — without an API key it still extracts, indexes, retrieves, and shows the relevant source passages.
- **Local-first** — text extraction, embeddings, and vector search all run on your machine; only generation calls a hosted LLM.

## How it works

| Stage | Technology | Role |
|---|---|---|
| **1. Extraction** | PyMuPDF, python-docx, pytesseract (optional) | Read PDFs, Word files, text files, and OCR images/scanned pages into clean text |
| **2. Retrieval** | sentence-transformers (`all-MiniLM-L6-v2`) + ChromaDB | Chunk the text, embed it locally, and search for the passages most relevant to your topic |
| **3. Generation** | GroqCloud (`llama-3.1-8b-instant`) | Write quizzes, flashcards, explanations, and Q&A grounded strictly in the retrieved snippets |
| **4. Classification** *(optional)* | Groq, or a local keyword + readability heuristic | Tag topics and an overall difficulty for the document |

---

## Requirements

- **Python 3.10+**
- A free **GroqCloud API key** (optional, but required for AI-generated content)
- **Tesseract OCR** (optional, only for reading images and scanned PDFs)

## Setup

### 1. Clone and install dependencies

```powershell
git clone https://github.com/mmaslov007/SDEV378-Final-AI.git
cd SDEV378-Final-AI

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

> All packages install into the local `.venv` folder only — nothing is installed
> system-wide.

### 2. Configure your environment

```powershell
copy .env.example .env
```

Edit `.env` and add your Groq API key (never commit this file):

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | For AI generation | Your GroqCloud key. Without it, the app runs in source-only fallback mode. |
| `GROQ_MODEL` | No | LLM model id (default: `llama-3.1-8b-instant`). |
| `STUDY_ASSISTANT_CHROMA_PATH` | No | Where ChromaDB stores its local index (default: `.chroma`). |
| `TESSERACT_CMD` | No | Path to `tesseract.exe`, only if it isn't on your `PATH`. |

### 3. (Optional) Install Tesseract for image OCR

Only needed for **scanned images or picture-only PDFs**. Normal PDFs, Word
documents, text files, and pasted notes work without it.

```powershell
# Windows
winget install --id tesseract-ocr.tesseract --exact --accept-source-agreements --accept-package-agreements
```

```bash
# macOS / Linux
brew install tesseract
sudo apt-get install tesseract-ocr
```

Reopen your terminal afterward so `PATH` refreshes. If OCR still shows as
unavailable, set `TESSERACT_CMD` in `.env`.

---

## Running the app

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The app opens in your browser at `http://localhost:8501`. The first retrieval run
downloads the MiniLM embedding model (~90 MB) into your local cache. Press
`Ctrl+C` in the terminal to stop the server.

### Using it — the happy path

1. **Material** — upload a file, paste notes, or click **Load Sample**.
2. **Extract Material** — pulls the text and shows an editable preview.
3. **Configure** — choose a mode (quiz / flashcards / explanation / Q&A), topic, and difficulty.
4. **Build Search Index** — chunks and indexes the text. *(Required before generating.)*
5. **Generate Study Set** — produces the study content with linked sources.

> **Generate** stays disabled until you build the index — that's the intended
> order, not a bug.

### Reading the status bar

The top navigation shows live component status:

| Indicator | Meaning |
|---|---|
| **OCR: off** | Tesseract isn't installed. Fine unless you need image/scanned-PDF OCR. |
| **LLM: ready / off** | `ready` once `GROQ_API_KEY` is set; otherwise the app runs in fallback mode. |
| **Retrieval: not built** | No index built *yet this session*. Flips to `chromadb` after you click **Build Search Index**. |

---

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m compileall study_assistant tests app.py
.\.venv\Scripts\python.exe scripts\check_setup.py
```

`check_setup.py` prints a quick diagnostic of installed dependencies, your Groq
key status, and Tesseract availability.

## Project structure

```
app.py                       Streamlit entry point (UI + page flow)
study_assistant/
  extraction.py              File/text extraction + OCR
  retrieval.py               Chunking, embeddings, ChromaDB / in-memory search
  generation.py              Groq-backed quiz/flashcard/explanation/Q&A generation
  classification.py          Topic + difficulty tagging (LLM or heuristic)
  config.py                  Environment configuration
  ui.py                      Design system (theme, nav, hero, components)
tests/                       Unit tests
scripts/check_setup.py       Environment diagnostics
sample_materials/            Demo content
.streamlit/config.toml       Theme configuration
```

## Troubleshooting

- **"PyMuPDF is not installed"** — you're running from the wrong Python. Stop any old Streamlit servers and relaunch with `.\.venv\Scripts\python.exe -m streamlit run app.py`.
- **OCR unavailable after installing Tesseract** — reopen your terminal, run `scripts\check_setup.py`, and set `TESSERACT_CMD` in `.env` if needed.
- **Want a quick demo?** — use `sample_materials/sdev378_ai_study_notes.txt` via the **Load Sample** button.

---

## Privacy & data

StudyAI runs locally and writes only a `.chroma/` index folder and a cached
embedding model to disk. The only outbound network calls are to **GroqCloud**
(for generation) and **Hugging Face** (a one-time model download). Text you
upload is sent to Groq's API to generate study content, so avoid uploading
sensitive material.
