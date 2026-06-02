"""Streamlit entry point for the AI Study Assistant."""

import streamlit as st


def main() -> None:
    st.set_page_config(
        page_title="AI Study Assistant",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("AI Study Assistant")
    st.caption("Upload or paste study material, then generate source-grounded practice.")

    st.info("Project scaffold is ready. The AI pipeline will be added in the next phases.")


if __name__ == "__main__":
    main()
