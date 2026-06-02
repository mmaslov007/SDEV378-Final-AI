"""Runtime configuration for local and hosted AI components."""

from __future__ import annotations

from dataclasses import dataclass
import os


DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
DEFAULT_CHROMA_PATH = ".chroma"


@dataclass(frozen=True, slots=True)
class AppConfig:
    groq_api_key: str
    groq_model: str
    chroma_path: str


def load_config() -> AppConfig:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    return AppConfig(
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        groq_model=os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL,
        chroma_path=os.getenv("STUDY_ASSISTANT_CHROMA_PATH", DEFAULT_CHROMA_PATH).strip() or DEFAULT_CHROMA_PATH,
    )
