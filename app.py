import streamlit as st
import tempfile
import os
from components.sidebar import show_sidebar
from core.rag_core import (
    create_conversational_rag_chain,
    load_document,
    auto_select_chunk_size,
)
from langchain_core.messages import HumanMessage, AIMessage

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="DocuQuery", page_icon="📄", layout="wide")


# --- CUSTOM CSS ---
def load_css(file_path):
    with open(file_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


load_css("assets/styles.css")


# --- SESSION STATE INITIALIZATION ---
def initialize_session_state():
    """Initializes session state variables if they don't exist."""
    defaults = {
        "messages": [
            {
                "role": "assistant",
                "content": "Hi there! Upload a document and ask me anything about it.",
            }
        ],
        "rag_chain": None,
        "api_key": "",
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "uploaded_file_name": None,
        "manual_mode": False,
        "uploaded_file_obj": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# --- HELPER FUNCTIONS ---
def format_chat_history(messages):
    """Formats chat history for LangChain by converting dicts to message objects."""
    history = []
    for msg in messages[1:]:  # Skip the initial assistant greeting
        if msg["role"] == "user":
            history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            history.append(AIMessage(content=msg["content"]))
    return history


# --- UI COMPONENTS & LOGIC ---
def display_header():
    """Displays the main header and subheader."""
    st.title("📄 DocuQuery")
    st.markdown("Upload a document to start a conversation. Supports PDF, Word, TXT.")


def display_chat_history():
    """Displays the chat messages and sources from session state."""
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if "sources" in msg and msg["sources"]:
                with st.expander("View Sources"):
                    for i, doc in enumerate(msg["sources"]):
                        st.info(
                            f"Source {i+1} (Page {doc.metadata.get('page', 'N/A')}):\n\n{doc.page_content[:300]}..."
                        )


def handle_document_processing(
    uploaded_file, api_key, mode, manual_chunk_size, manual_chunk_overlap
):
    """Handles the entire Stage 1 processing pipeline for a document."""
    with st.spinner("Processing document... This may take a moment."):
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=os.path.splitext(uploaded_file.name)[1]
            ) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name

            st.session_state.uploaded_file_name = uploaded_file.name
            documents = load_document(tmp_file_path)

            if mode == "Automatic":
                chunk_size, chunk_overlap = auto_select_chunk_size(documents)
                st.toast(
                    f"Optimal settings applied: Chunk Size={chunk_size}, Overlap={chunk_overlap}",
                    icon="🤖",
                )
            else:  # Manual mode
                chunk_size, chunk_overlap = manual_chunk_size, manual_chunk_overlap
                st.toast(
                    f"Using manual settings: Chunk Size={chunk_size}, Overlap={chunk_overlap}",
                    icon="🔧",
                )

            st.session_state.rag_chain = create_conversational_rag_chain(
                documents, api_key, chunk_size, chunk_overlap
            )
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": f"✅ Ready! Ask me anything about '{uploaded_file.name}'.",
                }
            ]
            st.rerun()

        except Exception as e:
            st.error(f"Failed to process document: {e}")
            st.session_state.rag_chain = None
        finally:
            if "tmp_file_path" in locals() and os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)


# --- MAIN APPLICATION ---
def main():
    """The main function that orchestrates the entire application."""
    initialize_session_state()
    api_key, mode, manual_chunk_size, manual_chunk_overlap = show_sidebar()
    display_header()

    uploaded_file = st.file_uploader(
        "Drag and drop or browse",
        type=["pdf", "docx", "txt"],
        label_visibility="collapsed",
    )

    # Persist the uploaded file object in session state for reprocessing
    if uploaded_file:
        st.session_state.uploaded_file_obj = uploaded_file

    # Safely get and remove the reprocess trigger flag so it only runs once
    should_reprocess = st.session_state.pop("trigger_reprocess", False)

    # Define the conditions under which the document processing should run
    is_new_file_uploaded = uploaded_file and (
        uploaded_file.name != st.session_state.get("uploaded_file_name")
    )
    is_reprocess_triggered = (
        should_reprocess and st.session_state.get("uploaded_file_obj") is not None
    )

    if is_new_file_uploaded or is_reprocess_triggered:
        if not api_key:
            st.warning(
                "Please enter your Google Gemini API key to process the document."
            )
        else:
            # Determine which file to process: the new one or the existing one for reprocessing
            file_to_process = uploaded_file or st.session_state.get("uploaded_file_obj")
            handle_document_processing(
                file_to_process, api_key, mode, manual_chunk_size, manual_chunk_overlap
            )

    st.divider()
    display_chat_history()

    if prompt := st.chat_input("Ask a question..."):
        if st.session_state.rag_chain is None:
            st.warning("Please upload and process a document first.")
            return

        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    chat_history = format_chat_history(st.session_state.messages)
                    response = st.session_state.rag_chain.invoke(
                        {"input": prompt, "chat_history": chat_history}
                    )
                    bot_message = {
                        "role": "assistant",
                        "content": response.get("answer"),
                        "sources": response.get("context", []),
                    }
                    st.session_state.messages.append(bot_message)
                    st.rerun()
                except Exception as e:
                    error_msg = f"An error occurred: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_msg}
                    )


if __name__ == "__main__":
    main()
