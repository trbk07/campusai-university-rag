"""Optional Streamlit UI entry point.

The UI is intentionally dependency-optional; use ``create_ui`` from an installed
Streamlit environment and inject the same pipeline used by the API.
"""
def create_ui(pipeline) -> None:
    try:
        import streamlit as st
    except ImportError as exc:
        raise RuntimeError("Install Streamlit to run the UI") from exc
    st.title("Adaptive Financial RAG")
    question = st.text_input("Câu hỏi")
    if question:
        response = pipeline.answer(question)
        st.write(response.answer)
        st.write({"citations": response.citations, "verification": response.verification})
