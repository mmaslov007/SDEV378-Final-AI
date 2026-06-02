"""Document extraction helpers for uploaded or pasted study material."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import shutil
from typing import Any


TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".csv"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


@dataclass(slots=True)
class ExtractedDocument:
    """Normalized extraction result shown to users before indexing."""

    source_name: str
    source_type: str
    text: str
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_text(self) -> bool:
        return bool(self.text.strip())

    @property
    def character_count(self) -> int:
        return len(self.text)


def normalize_text(text: str) -> str:
    """Clean noisy extraction text while preserving paragraph breaks."""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def get_tesseract_command() -> str | None:
    configured_path = os.getenv("TESSERACT_CMD", "").strip()
    if configured_path:
        return configured_path if Path(configured_path).exists() else shutil.which(configured_path)
    return shutil.which("tesseract")


def is_tesseract_available() -> bool:
    command = get_tesseract_command()
    return bool(command and Path(command).exists())


def extract_from_plain_text(text: str, source_name: str = "pasted notes") -> ExtractedDocument:
    normalized = normalize_text(text)
    warnings = []
    if not normalized:
        warnings.append("No readable text was provided.")
    return ExtractedDocument(
        source_name=source_name,
        source_type="text",
        text=normalized,
        warnings=warnings,
        metadata={"characters": len(normalized)},
    )


def extract_from_bytes(file_name: str, content: bytes) -> ExtractedDocument:
    suffix = Path(file_name).suffix.lower()

    if suffix in TEXT_EXTENSIONS or not suffix:
        return _extract_text_file(file_name, content)
    if suffix == ".pdf":
        return _extract_pdf(file_name, content)
    if suffix in IMAGE_EXTENSIONS:
        return _extract_image(file_name, content)

    return ExtractedDocument(
        source_name=file_name,
        source_type="unsupported",
        text="",
        warnings=[f"Unsupported file type: {suffix or 'unknown'}."],
        metadata={"extension": suffix},
    )


def _extract_text_file(file_name: str, content: bytes) -> ExtractedDocument:
    warnings: list[str] = []
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1", errors="replace")
        warnings.append("File was not valid UTF-8, so it was decoded with replacement characters.")

    normalized = normalize_text(text)
    if not normalized:
        warnings.append("The text file did not contain readable text.")

    return ExtractedDocument(
        source_name=file_name,
        source_type="text",
        text=normalized,
        warnings=warnings,
        metadata={"characters": len(normalized)},
    )


def _extract_pdf(file_name: str, content: bytes) -> ExtractedDocument:
    warnings: list[str] = []
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError:
        return ExtractedDocument(
            source_name=file_name,
            source_type="pdf",
            text="",
            warnings=["PyMuPDF is not installed, so PDF extraction is unavailable."],
            metadata={"pages": 0},
        )

    page_texts: list[str] = []
    ocr_pages = 0

    try:
        with fitz.open(stream=content, filetype="pdf") as document:
            for page_index, page in enumerate(document, start=1):
                page_text = normalize_text(page.get_text("text"))
                if page_text:
                    page_texts.append(page_text)
                    continue

                ocr_text = _ocr_pdf_page(page)
                if ocr_text:
                    ocr_pages += 1
                    page_texts.append(ocr_text)
                else:
                    warnings.append(f"Page {page_index} did not contain extractable text.")

            page_count = document.page_count
    except Exception as exc:
        return ExtractedDocument(
            source_name=file_name,
            source_type="pdf",
            text="",
            warnings=[f"PDF extraction failed: {exc}"],
            metadata={"pages": 0},
        )

    text = normalize_text("\n\n".join(page_texts))
    if not text:
        warnings.append("No readable text was found in the PDF.")
    if ocr_pages:
        warnings.append(f"OCR was used on {ocr_pages} PDF page(s).")

    return ExtractedDocument(
        source_name=file_name,
        source_type="pdf",
        text=text,
        warnings=warnings,
        metadata={"pages": page_count, "ocr_pages": ocr_pages, "characters": len(text)},
    )


def _ocr_pdf_page(page: Any) -> str:
    if not is_tesseract_available():
        return ""

    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        return ""

    _configure_pytesseract(pytesseract)
    pixmap = page.get_pixmap(dpi=200)
    mode = "RGBA" if pixmap.alpha else "RGB"
    image = Image.frombytes(mode, [pixmap.width, pixmap.height], pixmap.samples)
    return normalize_text(pytesseract.image_to_string(image))


def _extract_image(file_name: str, content: bytes) -> ExtractedDocument:
    warnings: list[str] = []
    if not is_tesseract_available():
        return ExtractedDocument(
            source_name=file_name,
            source_type="image",
            text="",
            warnings=["Tesseract is not installed, so image OCR is unavailable."],
            metadata={"ocr_available": False},
        )

    try:
        from io import BytesIO

        from PIL import Image
        import pytesseract
    except ImportError:
        return ExtractedDocument(
            source_name=file_name,
            source_type="image",
            text="",
            warnings=["Pillow or pytesseract is not installed, so image OCR is unavailable."],
            metadata={"ocr_available": True},
        )

    _configure_pytesseract(pytesseract)
    image = Image.open(BytesIO(content))
    text = normalize_text(pytesseract.image_to_string(image))
    if not text:
        warnings.append("OCR did not find readable text in the image.")

    return ExtractedDocument(
        source_name=file_name,
        source_type="image",
        text=text,
        warnings=warnings,
        metadata={"ocr_available": True, "characters": len(text)},
    )


def _configure_pytesseract(pytesseract_module: Any) -> None:
    command = get_tesseract_command()
    if command:
        pytesseract_module.pytesseract.tesseract_cmd = command
