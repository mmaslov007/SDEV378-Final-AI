"""Print dependency and environment status for local setup troubleshooting."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from study_assistant.config import load_config
from study_assistant.extraction import get_tesseract_command, is_tesseract_available


DEPENDENCIES = {
    "streamlit": "streamlit",
    "PyMuPDF": "fitz",
    "pytesseract": "pytesseract",
    "Pillow": "PIL",
    "ChromaDB": "chromadb",
    "sentence-transformers": "sentence_transformers",
    "Groq": "groq",
}


def main() -> None:
    config = load_config()
    print(f"Python: {sys.executable}")
    print(f"Groq key present: {bool(config.groq_api_key)}")
    print(f"Groq model: {config.groq_model}")
    print(f"Tesseract available: {is_tesseract_available()}")
    print(f"Tesseract command: {get_tesseract_command() or 'not found'}")
    print()
    print("Dependencies:")
    for label, module_name in DEPENDENCIES.items():
        status = "ok" if importlib.util.find_spec(module_name) else "missing"
        print(f"- {label}: {status}")


if __name__ == "__main__":
    main()
