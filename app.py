"""Streamlit entry point for the AI Study Assistant."""

from pathlib import Path

import streamlit as st

from study_assistant.config import load_config
from study_assistant.extraction import ExtractedDocument, extract_from_bytes, extract_from_plain_text, is_tesseract_available
from study_assistant.generation import StudyItem, StudyOutput, generate_study_output
from study_assistant.retrieval import SearchResult, build_index


SAMPLE_PATH = Path("sample_materials/sdev378_ai_study_notes.txt")


def main() -> None:
    st.set_page_config(
        page_title="AI Study Assistant",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _initialize_state()
    config = load_config()

    st.title("AI Study Assistant")
    st.caption("Source-grounded quizzes, flashcards, and explanations from your study material.")

    settings = _render_sidebar(config)

    input_column, pipeline_column = st.columns([1.1, 0.9], gap="large")
    with input_column:
        _render_input_panel()
        _render_preview_panel()

    with pipeline_column:
        _render_pipeline_panel(settings, config)

    output = st.session_state.get("study_output")
    if output:
        st.divider()
        _render_output(output)


def _initialize_state() -> None:
    defaults = {
        "extracted_doc": None,
        "text_preview": "",
        "retrieval_results": [],
        "study_output": None,
        "chunks": [],
        "index_backend": "",
        "index_warnings": [],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _render_sidebar(config) -> dict[str, str | int | bool]:
    with st.sidebar:
        st.header("Settings")
        mode = st.segmented_control(
            "Mode",
            ["quiz", "flashcards", "explanation"],
            default="quiz",
        )
        topic = st.text_input("Topic", placeholder="retrieval, OCR, final project standards")
        difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=1)
        count = st.slider("Items", min_value=1, max_value=8, value=4)
        retrieve_count = st.slider("Source snippets", min_value=1, max_value=8, value=4)
        chunk_size = st.slider("Chunk size", min_value=80, max_value=320, value=180, step=20)
        overlap = st.slider("Chunk overlap", min_value=0, max_value=80, value=35, step=5)
        prefer_chroma = st.toggle("Use ChromaDB", value=True)

        st.divider()
        st.subheader("Component Status")
        st.write(f"OCR: {'available' if is_tesseract_available() else 'not installed'}")
        st.write(f"LLM: {'configured' if config.groq_api_key else 'waiting for GROQ_API_KEY'}")
        st.write(f"Model: `{config.groq_model}`")
        backend = st.session_state.get("index_backend") or "not built"
        st.write(f"Retrieval: {backend}")

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
    st.subheader("Material")
    uploaded_file = st.file_uploader(
        "Upload",
        type=["pdf", "png", "jpg", "jpeg", "txt", "md", "csv"],
    )
    pasted_text = st.text_area("Paste", height=180, placeholder="Paste notes, slides text, or a reading excerpt.")

    button_column_1, button_column_2 = st.columns(2)
    with button_column_1:
        if st.button("Extract Material", use_container_width=True):
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


def _render_preview_panel() -> None:
    document: ExtractedDocument | None = st.session_state.get("extracted_doc")
    if document:
        metric_columns = st.columns(3)
        metric_columns[0].metric("Source", document.source_name)
        metric_columns[1].metric("Type", document.source_type)
        metric_columns[2].metric("Characters", document.character_count)
        for warning in document.warnings:
            st.warning(warning)

    st.text_area("Preview", key="text_preview", height=260)


def _render_pipeline_panel(settings: dict[str, str | int | bool], config) -> None:
    st.subheader("Pipeline")

    build_disabled = not bool(st.session_state.get("text_preview", "").strip())
    if st.button("Build Search Index", disabled=build_disabled, use_container_width=True):
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
    if st.button("Generate Study Set", disabled=generate_disabled, use_container_width=True):
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

    if results:
        with st.expander("Retrieved source snippets", expanded=False):
            _render_sources({f"S{index}": result.chunk.text for index, result in enumerate(results, start=1)})


def _build_search_index(settings: dict[str, str | int | bool], config) -> None:
    document: ExtractedDocument | None = st.session_state.get("extracted_doc")
    source_name = document.source_name if document else "study-material"
    text = st.session_state.get("text_preview", "")
    query = str(settings["topic"]).strip() or "important study concepts"

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


def _render_output(output: StudyOutput) -> None:
    st.subheader(output.title)
    status_columns = st.columns(3)
    status_columns[0].metric("Mode", output.mode)
    status_columns[1].metric("Items", len(output.items))
    status_columns[2].metric("LLM", "used" if output.used_llm else "fallback")

    for warning in output.warnings:
        st.warning(warning)

    if output.mode == "quiz":
        _render_quiz(output)
    elif output.mode == "flashcards":
        _render_flashcards(output.items, output.source_snippets)
    else:
        _render_explanations(output.items, output.source_snippets)


def _render_quiz(output: StudyOutput) -> None:
    selections: dict[int, str] = {}
    with st.form("quiz_answers"):
        for index, item in enumerate(output.items, start=1):
            choices = list(dict.fromkeys([*item.choices, item.answer]))
            selections[index] = st.radio(
                f"{index}. {item.prompt}",
                choices or [item.answer],
                key=f"quiz_choice_{index}",
            )
        submitted = st.form_submit_button("Review Answers")

    if submitted:
        for index, item in enumerate(output.items, start=1):
            selected = selections[index]
            correct = selected.strip().lower() == item.answer.strip().lower()
            st.write(f"**{index}. {'Correct' if correct else 'Review'}**")
            st.write(f"Answer: {item.answer}")
            st.write(item.explanation)
            _render_item_sources(item, output.source_snippets)


def _render_flashcards(items: list[StudyItem], source_snippets: dict[str, str]) -> None:
    for index, item in enumerate(items, start=1):
        front = item.front or item.prompt
        with st.expander(f"{index}. {front}", expanded=index == 1):
            st.write(item.back or item.answer)
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
