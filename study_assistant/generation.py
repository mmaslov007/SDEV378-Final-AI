"""Groq-backed generation for quizzes, flashcards, and explanations."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any

from study_assistant.config import DEFAULT_GROQ_MODEL
from study_assistant.retrieval import SearchResult


SUPPORTED_MODES = {"quiz", "flashcards", "explanation"}


@dataclass(slots=True)
class StudyItem:
    kind: str
    prompt: str
    answer: str
    explanation: str
    sources: list[str]
    choices: list[str] = field(default_factory=list)
    front: str = ""
    back: str = ""
    heading: str = ""
    key_points: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StudyOutput:
    mode: str
    title: str
    items: list[StudyItem]
    source_snippets: dict[str, str]
    warnings: list[str] = field(default_factory=list)
    model: str = DEFAULT_GROQ_MODEL

    @property
    def used_llm(self) -> bool:
        return not any("LLM unavailable" in warning or "Groq generation failed" in warning for warning in self.warnings)


def generate_study_output(
    *,
    mode: str,
    topic: str,
    results: list[SearchResult],
    count: int = 5,
    difficulty: str = "medium",
    api_key: str = "",
    model: str = DEFAULT_GROQ_MODEL,
    client: Any | None = None,
) -> StudyOutput:
    mode = _normalize_mode(mode)
    count = max(1, min(count, 10))
    source_snippets = _source_snippets(results)

    if not source_snippets:
        return StudyOutput(
            mode=mode,
            title="No source material available",
            items=[],
            source_snippets={},
            warnings=["No retrieved source snippets were available for generation."],
            model=model,
        )

    if client is None and not api_key:
        return _fallback_output(
            mode=mode,
            topic=topic,
            source_snippets=source_snippets,
            count=count,
            model=model,
            warning="LLM unavailable because GROQ_API_KEY is not configured.",
        )

    try:
        groq_client = client or _make_groq_client(api_key)
        completion = groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _system_prompt()},
                {
                    "role": "user",
                    "content": _user_prompt(
                        mode=mode,
                        topic=topic,
                        count=count,
                        difficulty=difficulty,
                        source_snippets=source_snippets,
                    ),
                },
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content
        payload = _parse_json_object(content)
        return _normalize_llm_payload(
            payload=payload,
            mode=mode,
            source_snippets=source_snippets,
            model=model,
        )
    except Exception as exc:
        return _fallback_output(
            mode=mode,
            topic=topic,
            source_snippets=source_snippets,
            count=count,
            model=model,
            warning=f"Groq generation failed: {exc}",
        )


def _make_groq_client(api_key: str) -> Any:
    try:
        from groq import Groq
    except ImportError as exc:
        raise RuntimeError("groq is not installed. Install requirements.txt to enable LLM generation.") from exc

    return Groq(api_key=api_key)


def _system_prompt() -> str:
    return (
        "You generate study material only from provided source snippets. "
        "Do not introduce facts that are not supported by the snippets. "
        "Return valid JSON only."
    )


def _user_prompt(
    *,
    mode: str,
    topic: str,
    count: int,
    difficulty: str,
    source_snippets: dict[str, str],
) -> str:
    schema = {
        "title": "short title",
        "items": [
            {
                "question": "quiz question, or empty for non-quiz modes",
                "choices": ["A", "B", "C", "D"],
                "answer": "correct answer",
                "front": "flashcard front",
                "back": "flashcard back",
                "heading": "explanation heading",
                "summary": "short explanation paragraph",
                "key_points": ["supported point"],
                "explanation": "why this answer is correct, grounded in sources",
                "sources": ["S1"],
            }
        ],
    }
    snippets = "\n\n".join(f"{source_id}: {text}" for source_id, text in source_snippets.items())
    topic_text = topic.strip() or "the most important ideas in the source material"
    return (
        f"Mode: {mode}\n"
        f"Topic: {topic_text}\n"
        f"Difficulty: {difficulty}\n"
        f"Item count: {count}\n\n"
        "For quiz mode, create multiple-choice questions with exactly four choices. "
        "For flashcards mode, use front/back fields. "
        "For explanation mode, create concise explanations with key points. "
        "Every item must include one or more source ids from the snippets.\n\n"
        f"JSON schema example:\n{json.dumps(schema)}\n\n"
        f"Source snippets:\n{snippets}"
    )


def _normalize_llm_payload(
    *,
    payload: dict[str, Any],
    mode: str,
    source_snippets: dict[str, str],
    model: str,
) -> StudyOutput:
    title = str(payload.get("title") or _title_for_mode(mode)).strip()
    items_payload = payload.get("items", [])
    if not isinstance(items_payload, list):
        items_payload = []

    items = [
        _normalize_item(item, mode=mode, source_snippets=source_snippets)
        for item in items_payload
        if isinstance(item, dict)
    ]
    items = [item for item in items if item.prompt or item.front or item.heading]

    warnings: list[str] = []
    if not items:
        warnings.append("LLM response did not include usable study items.")

    return StudyOutput(
        mode=mode,
        title=title,
        items=items,
        source_snippets=source_snippets,
        warnings=warnings,
        model=model,
    )


def _normalize_item(item: dict[str, Any], *, mode: str, source_snippets: dict[str, str]) -> StudyItem:
    sources = [source for source in item.get("sources", []) if source in source_snippets]
    if not sources:
        sources = [next(iter(source_snippets))]

    choices = item.get("choices", [])
    if not isinstance(choices, list):
        choices = []
    choices = [str(choice).strip() for choice in choices if str(choice).strip()]

    key_points = item.get("key_points", [])
    if not isinstance(key_points, list):
        key_points = []
    key_points = [str(point).strip() for point in key_points if str(point).strip()]

    question = str(item.get("question") or "").strip()
    front = str(item.get("front") or "").strip()
    back = str(item.get("back") or "").strip()
    heading = str(item.get("heading") or "").strip()
    summary = str(item.get("summary") or "").strip()
    answer = str(item.get("answer") or item.get("back") or summary).strip()
    explanation = str(item.get("explanation") or summary or answer).strip()

    if mode == "quiz":
        prompt = question or front or heading
    elif mode == "flashcards":
        prompt = front or question or heading
    else:
        prompt = heading or question or front or _title_for_mode(mode)

    return StudyItem(
        kind=mode,
        prompt=prompt,
        answer=answer,
        explanation=explanation,
        sources=sources,
        choices=choices,
        front=front,
        back=back,
        heading=heading,
        key_points=key_points,
    )


def _fallback_output(
    *,
    mode: str,
    topic: str,
    source_snippets: dict[str, str],
    count: int,
    model: str,
    warning: str,
) -> StudyOutput:
    items: list[StudyItem] = []
    source_ids = list(source_snippets)
    for source_id in source_ids[:count]:
        snippet = source_snippets[source_id]
        sentence = _first_sentence(snippet)
        if mode == "quiz":
            items.append(
                StudyItem(
                    kind=mode,
                    prompt=f"Which source idea is most supported by {source_id}?",
                    choices=_fallback_choices(sentence, source_snippets),
                    answer=sentence,
                    explanation=f"{source_id} directly supports this answer.",
                    sources=[source_id],
                )
            )
        elif mode == "flashcards":
            front = f"{topic or 'Source review'}: {source_id}"
            items.append(
                StudyItem(
                    kind=mode,
                    prompt=front,
                    front=front,
                    back=sentence,
                    answer=sentence,
                    explanation=f"Derived from {source_id}.",
                    sources=[source_id],
                )
            )
        else:
            heading = f"Source-grounded explanation from {source_id}"
            items.append(
                StudyItem(
                    kind=mode,
                    prompt=heading,
                    heading=heading,
                    answer=sentence,
                    explanation=sentence,
                    key_points=[sentence],
                    sources=[source_id],
                )
            )

    return StudyOutput(
        mode=mode,
        title=_title_for_mode(mode),
        items=items,
        source_snippets=source_snippets,
        warnings=[warning],
        model=model,
    )


def _parse_json_object(content: str) -> dict[str, Any]:
    content = content.strip()
    content = re.sub(r"^```(?:json)?", "", content, flags=re.IGNORECASE).strip()
    content = re.sub(r"```$", "", content).strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        parsed = json.loads(content[start : end + 1])

    if not isinstance(parsed, dict):
        raise ValueError("LLM response JSON must be an object.")
    return parsed


def _source_snippets(results: list[SearchResult]) -> dict[str, str]:
    snippets: dict[str, str] = {}
    for index, result in enumerate(results, start=1):
        snippets[f"S{index}"] = result.chunk.text
    return snippets


def _normalize_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported study mode: {mode}")
    return normalized


def _first_sentence(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return parts[0] if parts and parts[0] else text[:180].strip()


def _fallback_choices(answer: str, source_snippets: dict[str, str]) -> list[str]:
    choices = [answer]
    for snippet in source_snippets.values():
        choice = _first_sentence(snippet)
        if choice and choice not in choices:
            choices.append(choice)
        if len(choices) == 4:
            break
    while len(choices) < 4:
        choices.append("Review the source snippets for supporting evidence.")
    return choices[:4]


def _title_for_mode(mode: str) -> str:
    if mode == "quiz":
        return "Source-Grounded Quiz"
    if mode == "flashcards":
        return "Source-Grounded Flashcards"
    return "Source-Grounded Explanation"
