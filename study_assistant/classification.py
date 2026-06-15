"""Lightweight topic and difficulty classification for uploaded study material.

Uses Groq when an API key is available, with a dependency-free heuristic
fallback (keyword frequency + a Flesch readability proxy) so the feature still
works offline and without external services.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import re
from typing import Any

from study_assistant.config import DEFAULT_GROQ_MODEL
from study_assistant.generation import _make_groq_client, _parse_json_object


DIFFICULTIES = ("easy", "medium", "hard")
_LLM_PROMPT_CHAR_LIMIT = 3000

STOPWORDS = {
    "about", "above", "after", "again", "against", "their", "them", "then",
    "there", "these", "they", "this", "those", "through", "under", "until",
    "while", "with", "your", "yours", "here", "have", "from", "that", "what",
    "when", "where", "which", "will", "would", "could", "should", "into",
    "over", "such", "than", "each", "other", "some", "more", "most", "much",
    "very", "also", "been", "being", "does", "done", "only", "just", "like",
    "make", "made", "many", "both", "between", "because", "before", "during",
    "using", "used", "uses", "able", "above", "below", "same", "shown",
}


@dataclass(slots=True)
class DocumentTags:
    """Auto-detected labels shown to help users choose topic and difficulty."""

    topics: list[str]
    difficulty: str
    used_llm: bool = False
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_topics(self) -> bool:
        return bool(self.topics)


def classify_document(
    text: str,
    *,
    max_topics: int = 5,
    api_key: str = "",
    model: str = DEFAULT_GROQ_MODEL,
    client: Any | None = None,
) -> DocumentTags:
    """Return detected topics and an overall difficulty for the material."""

    text = text.strip()
    if not text:
        return DocumentTags(
            topics=[],
            difficulty="medium",
            warnings=["No text was available to classify."],
            metadata={"method": "none"},
        )

    if client is None and not api_key:
        return _heuristic_tags(text, max_topics)

    try:
        groq_client = client or _make_groq_client(api_key)
        completion = groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": _user_prompt(text, max_topics)},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        payload = _parse_json_object(completion.choices[0].message.content)
        return _normalize_llm_tags(payload, max_topics=max_topics, fallback_text=text)
    except Exception as exc:
        tags = _heuristic_tags(text, max_topics)
        tags.warnings.append(f"Auto-tagging fell back to local analysis: {exc}")
        return tags


def _system_prompt() -> str:
    return (
        "You label study material. Identify the main topics and an overall "
        "difficulty. Return valid JSON only."
    )


def _user_prompt(text: str, max_topics: int) -> str:
    excerpt = text[:_LLM_PROMPT_CHAR_LIMIT]
    return (
        f"Identify up to {max_topics} short topic labels and one overall "
        "difficulty (easy, medium, or hard) for the study material below.\n"
        'Return JSON: {"topics": ["..."], "difficulty": "easy|medium|hard"}\n\n'
        f"Study material:\n{excerpt}"
    )


def _normalize_llm_tags(payload: dict[str, Any], *, max_topics: int, fallback_text: str) -> DocumentTags:
    topics_payload = payload.get("topics", [])
    if not isinstance(topics_payload, list):
        topics_payload = []
    topics = [str(topic).strip() for topic in topics_payload if str(topic).strip()][:max_topics]
    if not topics:
        topics = _keyword_topics(fallback_text, max_topics)

    difficulty = str(payload.get("difficulty", "")).strip().lower()
    if difficulty not in DIFFICULTIES:
        difficulty = _estimate_difficulty(fallback_text)

    return DocumentTags(
        topics=topics,
        difficulty=difficulty,
        used_llm=True,
        metadata={"method": "llm"},
    )


def _heuristic_tags(text: str, max_topics: int) -> DocumentTags:
    return DocumentTags(
        topics=_keyword_topics(text, max_topics),
        difficulty=_estimate_difficulty(text),
        used_llm=False,
        metadata={"method": "heuristic"},
    )


def _keyword_topics(text: str, max_topics: int) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z'\-]+", text.lower())
    counts = Counter(token for token in tokens if len(token) >= 4 and token not in STOPWORDS)
    return [word.title() for word, _ in counts.most_common(max_topics)]


def _estimate_difficulty(text: str) -> str:
    sentence_count = max(1, len(re.findall(r"[.!?]+", text)))
    words = re.findall(r"[a-zA-Z]+", text)
    word_count = max(1, len(words))
    syllables = sum(_count_syllables(word) for word in words)

    flesch = 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllables / word_count)
    if flesch >= 70:
        return "easy"
    if flesch >= 45:
        return "medium"
    return "hard"


def _count_syllables(word: str) -> int:
    word = word.lower()
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)
