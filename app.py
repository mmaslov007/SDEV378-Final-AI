"""Streamlit entry point for the AI Study Assistant."""

import random
from pathlib import Path

import streamlit as st

from study_assistant.classification import DocumentTags, classify_document
from study_assistant.config import load_config
from study_assistant.extraction import ExtractedDocument, extract_from_bytes, extract_from_plain_text, is_tesseract_available
from study_assistant.generation import StudyItem, StudyOutput, generate_study_output
from study_assistant.retrieval import SearchResult, build_index
from study_assistant import ui


SAMPLE_PATH = Path("sample_materials/sdev378_ai_study_notes.txt")
MODE_LABELS = {"quiz": "Quiz", "flashcards": "Flashcards", "explanation": "Explanation", "qa": "Q&A"}


def main() -> None:
    st.set_page_config(
        page_title="StudyAI — AI Study Assistant",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    ui.inject_global_styles()
    _initialize_state()
    config = load_config()

    # Landing page: sticky nav (with live status) + hero
    ui.render_nav(_status_items(config))
    ui.anchor("home")
    ui.render_hero()

    # Step-by-step workflow, centered and scrollable
    ui.anchor("material")
    with st.container(border=True):
        _render_input_panel()

    ui.anchor("preview")
    with st.container(border=True):
        _render_preview_panel()

    ui.anchor("configure")
    with st.container(border=True):
        settings = _render_config_panel()

    ui.anchor("generate")
    with st.container(border=True):
        _render_pipeline_panel(settings, config)

    output = st.session_state.get("study_output")
    if output:
        ui.anchor("results")
        with st.container(border=True):
            _render_output(output)

    ui.render_footer()


def _initialize_state() -> None:
    defaults = {
        "extracted_doc": None,
        "text_preview": "",
        "doc_tags": None,
        "retrieval_results": [],
        "study_output": None,
        "chunks": [],
        "index_backend": "",
        "index_warnings": [],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _status_items(config) -> list[tuple[str, str, str]]:
    ocr_ok = is_tesseract_available()
    llm_ok = bool(config.groq_api_key)
    backend = st.session_state.get("index_backend")
    return [
        ("OCR", "ready" if ocr_ok else "off", "ok" if ocr_ok else "off"),
        ("LLM", "ready" if llm_ok else "off", "ok" if llm_ok else "off"),
        ("Model", config.groq_model, "neutral"),
        ("Retrieval", backend or "not built", "ok" if backend else "off"),
    ]


def _render_config_panel() -> dict[str, str | int | bool]:
    ui.section_header("⚙️", "Configure", "Step 3 · Choose your study mode and tuning")
    mode = st.segmented_control(
        "Mode",
        ["quiz", "flashcards", "explanation", "qa"],
        default="quiz",
        format_func=lambda value: MODE_LABELS.get(value, value),
    )

    top_left, top_mid, top_right = st.columns(3)
    with top_left:
        topic = st.text_input("Topic", placeholder="retrieval, OCR, final project")
    with top_mid:
        difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=1)
    with top_right:
        count = st.slider("Items", min_value=1, max_value=8, value=4)

    with st.expander("Advanced retrieval settings", expanded=False):
        adv_left, adv_right = st.columns(2)
        with adv_left:
            retrieve_count = st.slider("Source snippets", min_value=1, max_value=8, value=4)
            chunk_size = st.slider("Chunk size", min_value=80, max_value=320, value=180, step=20)
        with adv_right:
            overlap = st.slider("Chunk overlap", min_value=0, max_value=80, value=35, step=5)
            prefer_chroma = st.toggle("Use ChromaDB", value=True)

    return {
        "mode": mode or "quiz",
        "topic": topic,
        "difficulty": difficulty,
        "count": count,
        "retrieve_count": retrieve_count,
        "chunk_size": chunk_size,
        "overlap": overlap,
        "prefer_chroma": prefer_chroma,
    }


def _render_input_panel() -> None:
    ui.section_header("📥", "Material", "Step 1 · Upload a file or paste your notes")
    uploaded_file = st.file_uploader(
        "Upload",
        type=["pdf", "docx", "png", "jpg", "jpeg", "txt", "md", "csv"],
    )
    pasted_text = st.text_area("Paste", height=100, placeholder="Paste notes, slides text, or a reading excerpt.")

    button_column_1, button_column_2 = st.columns(2)
    with button_column_1:
        if st.button("Extract Material", use_container_width=True, type="primary"):
            _extract_material(uploaded_file, pasted_text)
    with button_column_2:
        if st.button("Load Sample", use_container_width=True):
            sample_text = SAMPLE_PATH.read_text(encoding="utf-8")
            _store_extraction(extract_from_plain_text(sample_text, SAMPLE_PATH.name))


def _extract_material(uploaded_file, pasted_text: str) -> None:
    if uploaded_file is not None:
        document = extract_from_bytes(uploaded_file.name, uploaded_file.getvalue())
        _store_extraction(document)
        return

    if pasted_text.strip():
        _store_extraction(extract_from_plain_text(pasted_text))
        return

    st.warning("Add material first.")


def _store_extraction(document: ExtractedDocument) -> None:
    st.session_state.extracted_doc = document
    st.session_state.text_preview = document.text
    st.session_state.retrieval_results = []
    st.session_state.study_output = None
    st.session_state.chunks = []
    st.session_state.index_backend = ""
    st.session_state.index_warnings = []

    if document.has_text:
        config = load_config()
        st.session_state.doc_tags = classify_document(
            document.text,
            api_key=config.groq_api_key,
            model=config.groq_model,
        )
    else:
        st.session_state.doc_tags = None


def _render_preview_panel() -> None:
    ui.section_header("👁️", "Preview", "Step 2 · Review extracted text and detected topics")
    document: ExtractedDocument | None = st.session_state.get("extracted_doc")
    if document:
        metric_columns = st.columns(3)
        metric_columns[0].metric("Source", document.source_name)
        metric_columns[1].metric("Type", document.source_type)
        metric_columns[2].metric("Characters", document.character_count)
        for warning in document.warnings:
            st.warning(warning)

    tags: DocumentTags | None = st.session_state.get("doc_tags")
    if tags and tags.has_topics:
        method = "AI" if tags.used_llm else "auto"
        ui.chips(f"Topics · {method}", tags.topics)
        ui.chips("Difficulty", [tags.difficulty])

    if not document:
        ui.empty_hint("Nothing extracted yet", "Upload a file or load the sample, then press Extract Material.")

    st.text_area("Extracted text", key="text_preview", height=260, label_visibility="collapsed")


def _render_pipeline_panel(settings: dict[str, str | int | bool], config) -> None:
    ui.section_header("⚡", "Generate", "Step 4 · Build the index, then create your study set")

    build_disabled = not bool(st.session_state.get("text_preview", "").strip())
    if st.button("Build Search Index", disabled=build_disabled, use_container_width=True, type="primary"):
        _build_search_index(settings, config)

    chunks = st.session_state.get("chunks", [])
    results = st.session_state.get("retrieval_results", [])
    index_backend = st.session_state.get("index_backend")
    if chunks:
        metrics = st.columns(3)
        metrics[0].metric("Chunks", len(chunks))
        metrics[1].metric("Retrieved", len(results))
        metrics[2].metric("Backend", index_backend or "unknown")

    for warning in st.session_state.get("index_warnings", []):
        st.warning(warning)

    generate_disabled = not bool(results)
    if st.button("Generate Study Set", disabled=generate_disabled, use_container_width=True, type="primary"):
        with st.spinner("Generating your study set…"):
            output = generate_study_output(
                mode=str(settings["mode"]),
                topic=str(settings["topic"]),
                results=results,
                count=int(settings["count"]),
                difficulty=str(settings["difficulty"]),
                api_key=config.groq_api_key,
                model=config.groq_model,
            )
        st.session_state.study_output = output

    if generate_disabled and not chunks:
        ui.empty_hint("No index yet", "Build a search index above to unlock generation.")

    if results:
        with st.expander("Retrieved source snippets", expanded=False):
            _render_sources({f"S{index}": result.chunk.text for index, result in enumerate(results, start=1)})


def _build_search_index(settings: dict[str, str | int | bool], config) -> None:
    document: ExtractedDocument | None = st.session_state.get("extracted_doc")
    source_name = document.source_name if document else "study-material"
    text = st.session_state.get("text_preview", "")
    query = str(settings["topic"]).strip() or _detected_topic_query()

    store, chunks, warnings = build_index(
        text,
        source_name,
        query_hint=query,
        chunk_size=int(settings["chunk_size"]),
        overlap=int(settings["overlap"]),
        prefer_chroma=bool(settings["prefer_chroma"]),
        persist_path=config.chroma_path,
    )
    results: list[SearchResult] = store.query(query, limit=int(settings["retrieve_count"])) if chunks else []

    st.session_state.chunks = chunks
    st.session_state.retrieval_results = results
    st.session_state.index_backend = store.backend_name
    st.session_state.index_warnings = warnings
    st.session_state.study_output = None


def _detected_topic_query() -> str:
    tags: DocumentTags | None = st.session_state.get("doc_tags")
    if tags and tags.has_topics:
        return " ".join(tags.topics[:3])
    return "important study concepts"


def _render_output(output: StudyOutput) -> None:
    ui.section_header("🎓", output.title, "Step 5 · Your generated study set")
    status_columns = st.columns(3)
    status_columns[0].metric("Mode", MODE_LABELS.get(output.mode, output.mode))
    status_columns[1].metric("Items", len(output.items))
    status_columns[2].metric("Generation", "AI" if output.used_llm else "fallback")

    for warning in output.warnings:
        st.warning(warning)

    if output.mode == "quiz":
        _render_quiz(output)
    elif output.mode == "flashcards":
        _render_flashcards(output.items, output.source_snippets)
    elif output.mode == "qa":
        _render_qa(output.items, output.source_snippets)
    else:
        _render_explanations(output.items, output.source_snippets)


def _render_quiz(output: StudyOutput) -> None:
    selections: dict[int, str | None] = {}
    with st.form("quiz_answers"):
        for index, item in enumerate(output.items, start=1):
            selections[index] = st.radio(
                f"{index}. {item.prompt}",
                _quiz_choices(item, index),
                index=None,
                key=f"quiz_choice_{index}",
            )
        submitted = st.form_submit_button("Submit Answers", type="primary")

    if not submitted:
        return

    correct_count = 0
    for index, item in enumerate(output.items, start=1):
        selected = selections[index]
        is_correct = bool(selected) and selected.strip().lower() == item.answer.strip().lower()
        if is_correct:
            correct_count += 1
            st.success(f"{index}. Correct  ·  {item.prompt}")
        elif selected:
            st.error(f"{index}. Incorrect  ·  {item.prompt}")
        else:
            st.error(f"{index}. Not answered  ·  {item.prompt}")

        st.markdown(f"**Correct answer:** {item.answer}")
        if selected and not is_correct:
            st.markdown(f"**Your answer:** {selected}")
        if item.explanation and item.explanation != item.answer:
            st.write(item.explanation)
        _render_item_sources(item, output.source_snippets)
        st.divider()

    st.info(f"Score: {correct_count} / {len(output.items)} correct")


def _quiz_choices(item: StudyItem, seed: int) -> list[str]:
    """Deduplicate choices (ensuring the answer is present) and shuffle them
    deterministically so the correct option isn't always in the same spot but
    the order stays stable across reruns within a generated set."""
    choices = list(dict.fromkeys([*item.choices, item.answer]))
    if not choices:
        choices = [item.answer]
    random.Random(seed).shuffle(choices)
    return choices


def _render_flashcards(items: list[StudyItem], source_snippets: dict[str, str]) -> None:
    for index, item in enumerate(items, start=1):
        front = item.front or item.prompt
        with st.expander(f"{index}. {front}", expanded=index == 1):
            st.write(item.back or item.answer)
            if item.explanation and item.explanation != item.answer:
                st.caption(item.explanation)
            _render_item_sources(item, source_snippets)


def _render_qa(items: list[StudyItem], source_snippets: dict[str, str]) -> None:
    for index, item in enumerate(items, start=1):
        st.markdown(f"#### {index}. {item.prompt}")
        with st.expander("Show answer", expanded=False):
            st.write(item.answer)
            if item.explanation and item.explanation != item.answer:
                st.caption(item.explanation)
            _render_item_sources(item, source_snippets)


def _render_explanations(items: list[StudyItem], source_snippets: dict[str, str]) -> None:
    for index, item in enumerate(items, start=1):
        st.markdown(f"#### {index}. {item.heading or item.prompt}")
        st.write(item.explanation or item.answer)
        if item.key_points:
            for point in item.key_points:
                st.write(f"- {point}")
        _render_item_sources(item, source_snippets)


def _render_item_sources(item: StudyItem, source_snippets: dict[str, str]) -> None:
    selected_sources = {source: source_snippets[source] for source in item.sources if source in source_snippets}
    if selected_sources:
        with st.expander("Sources", expanded=False):
            _render_sources(selected_sources)


def _render_sources(source_snippets: dict[str, str]) -> None:
    for source_id, snippet in source_snippets.items():
        st.markdown(f"**{source_id}**")
        st.write(snippet)


if __name__ == "__main__":
    main()
