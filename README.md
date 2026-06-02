# AI Study Assistant Quiz Generator

An AI-enabled Streamlit study assistant that turns course materials into source-grounded quizzes, flashcards, explanations, and review snippets.

This project is built for the SDEV378 Applied AI final project standard: a functional proof of concept with at least three ML-based components working together in a meaningful way.

## ML Components

1. **Document extraction and OCR**
   - `PyMuPDF` extracts selectable PDF text locally.
   - `pytesseract` can OCR image uploads and PDF pages that do not contain extractable text.
   - Output: normalized study text plus extraction diagnostics.

2. **Semantic retrieval**
   - `sentence-transformers/all-MiniLM-L6-v2` creates local embeddings.
   - `ChromaDB` stores and searches chunks from the user's uploaded or pasted materials.
   - Output: source chunks ranked by semantic relevance.

3. **LLM study generation**
   - GroqCloud runs `llama-3.1-8b-instant` by default.
   - The generator receives retrieved snippets and produces quiz questions, flashcards, or explanations grounded in those snippets.
   - Output: structured study content plus source references.

## Happy Path

1. Upload or paste course material.
2. Preview extracted text and fix it if needed.
3. Build a local semantic index.
4. Choose quiz, flashcards, or explanation mode.
5. Generate study output using retrieved snippets.
6. Answer quiz questions and review explanations tied back to source text.

## Setup From GitHub

Clone the repository and enter the project folder:

```powershell
git clone https://github.com/mmaslov007/SDEV378-Final-AI.git
cd SDEV378-Final-AI
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create your local environment file:

```powershell
copy .env.example .env
```

Add your Groq API key to `.env`. Never commit this file:

```text
GROQ_API_KEY=your_key_here
```

Install Tesseract OCR for image uploads and scanned PDFs. On Windows, use one of these package-manager options:

```powershell
winget install --id tesseract-ocr.tesseract --exact --accept-source-agreements --accept-package-agreements
```

```powershell
choco install tesseract -y
```

Close and reopen PowerShell after installing Tesseract so PATH refreshes. If OCR still shows as unavailable, set the executable path in `.env`:

```text
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

For macOS or Linux:

```bash
brew install tesseract
sudo apt-get install tesseract-ocr
```

Run the app from the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The first semantic retrieval run may download the `sentence-transformers/all-MiniLM-L6-v2` model. Tesseract OCR is optional but recommended for images and scanned PDFs. If it is not installed, the app still supports pasted text and selectable PDF text.

## Validation

Run the dependency-light checks:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m compileall study_assistant tests app.py
.\.venv\Scripts\python.exe scripts\check_setup.py
```

Run the Streamlit app:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The app displays component status in the sidebar:

- OCR is available only when local Tesseract is installed.
- Retrieval uses ChromaDB and MiniLM when the full requirements are installed; otherwise it falls back to an in-memory hashing index.
- Generation uses Groq when `GROQ_API_KEY` is configured; otherwise it shows source-grounded fallback study prompts.

## Troubleshooting

If the app says `PyMuPDF is not installed`, it is running from the wrong Python environment. Stop any old Streamlit servers, then launch with the virtual environment command:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*streamlit*app.py*' -and $_.ProcessId -ne $PID } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If OCR still says unavailable after installing Tesseract, run:

```powershell
.\.venv\Scripts\python.exe scripts\check_setup.py
```

Then set `TESSERACT_CMD` in `.env` if needed.

## Demo Material

Use `sample_materials/sdev378_ai_study_notes.txt` for a reliable local demo without needing external files.

## Project Review Fit

- The interface is minimal but demo-ready.
- The app completes the intended study workflow end to end.
- The three AI components each do something distinct: OCR/extraction reads the material, embeddings retrieve the right parts, and the LLM creates study output from the retrieved evidence.
