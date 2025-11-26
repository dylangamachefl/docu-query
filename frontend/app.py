import streamlit as st
import requests
import os
from components.sidebar import show_sidebar

# --- CONFIGURATION ---
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="DocuQuery", page_icon="📄", layout="wide")


# --- CUSTOM CSS ---
def load_css(file_path):
    """Loads custom CSS from a file."""
    if os.path.exists(file_path):
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
        "document_processed": False,
        "uploaded_file_name": None,
        "uploaded_file_obj": None, # To hold the file object for reprocessing
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


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
            # Check for sources and handle the new dictionary format
            if "sources" in msg and msg["sources"]:
                with st.expander("View Sources"):
                    for i, doc in enumerate(msg["sources"]):
                        page_num = doc.get("metadata", {}).get("page", "N/A")
                        content_preview = doc.get("page_content", "")[:300]
                        st.info(f"Source {i+1} (Page {page_num}):\n\n{content_preview}...")

def handle_document_upload(uploaded_file, mode, manual_chunk_size, manual_chunk_overlap):
    """Sends the document and settings to the backend for processing."""
    with st.spinner("Processing document... This may take a moment."):
        try:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            data = {
                "mode": mode,
                "manual_chunk_size": manual_chunk_size,
                "manual_chunk_overlap": manual_chunk_overlap
            }
            response = requests.post(f"{BACKEND_URL}/upload", files=files, data=data)
            response.raise_for_status() # Raise an exception for bad status codes

            st.session_state.document_processed = True
            st.session_state.uploaded_file_name = uploaded_file.name
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": f"✅ Ready! Ask me anything about '{uploaded_file.name}'.",
                }
            ]
            st.success("Document processed successfully!")
            st.rerun()

        except requests.exceptions.RequestException as e:
            st.error(f"Failed to connect to backend: {e}")
            st.session_state.document_processed = False
        except Exception as e:
            st.error(f"Failed to process document: {e}")
            st.session_state.document_processed = False


# --- MAIN APPLICATION ---
def main():
    """The main function that orchestrates the entire application."""
    initialize_session_state()
    mode, manual_chunk_size, manual_chunk_overlap = show_sidebar()
    display_header()

    uploaded_file = st.file_uploader(
        "Drag and drop or browse",
        type=["pdf", "docx", "txt"],
        label_visibility="collapsed",
    )

    if uploaded_file:
        st.session_state.uploaded_file_obj = uploaded_file

    should_reprocess = st.session_state.pop("trigger_reprocess", False)

    is_new_file = uploaded_file and (uploaded_file.name != st.session_state.uploaded_file_name)
    is_reprocess = should_reprocess and st.session_state.uploaded_file_obj is not None

    if is_new_file or is_reprocess:
        file_to_process = uploaded_file or st.session_state.uploaded_file_obj
        handle_document_upload(file_to_process, mode, manual_chunk_size, manual_chunk_overlap)

    st.divider()
    display_chat_history()

    if prompt := st.chat_input("Ask a question..."):
        if not st.session_state.document_processed:
            st.warning("Please upload and process a document first.")
            return

        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    payload = {
                        "input_text": prompt,
                        "chat_history": st.session_state.messages[:-1], # Exclude the current prompt
                        "uploaded_file_name": st.session_state.uploaded_file_name,
                        "mode": mode,
                        "manual_chunk_size": manual_chunk_size,
                        "manual_chunk_overlap": manual_chunk_overlap,
                    }
                    response = requests.post(f"{BACKEND_URL}/query", json=payload)
                    response.raise_for_status()

                    bot_response = response.json()
                    bot_message = {
                        "role": "assistant",
                        "content": bot_response.get("answer"),
                        "sources": bot_response.get("sources", []),
                    }
                    st.session_state.messages.append(bot_message)
                    st.rerun()

                except requests.exceptions.RequestException as e:
                    error_msg = f"Error communicating with backend: {e}"
                    st.error(error_msg)
                except Exception as e:
                    error_msg = f"An unexpected error occurred: {str(e)}"
                    st.error(error_msg)


if __name__ == "__main__":
    main()
