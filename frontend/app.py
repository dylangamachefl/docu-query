import streamlit as st
import requests
import os
from components.sidebar import show_sidebar
from components.data_extraction import show_extraction_ui

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

    # --- TABS FOR CHAT AND DATA EXTRACTION ---
    tab1, tab2 = st.tabs(["💬 Chat", "📊 Data Extraction"])

    with tab1:
        display_chat_history()
        if prompt := st.chat_input("Ask a question..."):
            if not st.session_state.document_processed:
                st.warning("Please upload and process a document first.")
                return

            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)

            with st.chat_message("assistant"):
                try:
                    payload = {
                        "input_text": prompt,
                        "chat_history": [
                            msg for msg in st.session_state.messages if msg["role"] != "sources"
                        ],
                        "uploaded_file_name": st.session_state.uploaded_file_name,
                    }

                    def stream_generator():
                        """Generator to stream response from the backend."""
                        with requests.post(
                            f"{BACKEND_URL}/stream_chat", json=payload, stream=True
                        ) as response:
                            response.raise_for_status()
                            for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                                yield chunk

                    full_response = st.write_stream(stream_generator)

                    # Fetch sources after the stream is complete
                    sources_response = requests.get(
                        f"{BACKEND_URL}/get_sources/{st.session_state.uploaded_file_name}"
                    )
                    sources = sources_response.json() if sources_response.status_code == 200 else []

                    bot_message = {
                        "role": "assistant",
                        "content": full_response,
                        "sources": sources,
                    }
                    st.session_state.messages.append(bot_message)
                    st.rerun()

                except requests.exceptions.RequestException as e:
                    st.error(f"Error communicating with backend: {e}")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {str(e)}")

    with tab2:
        show_extraction_ui(BACKEND_URL)


if __name__ == "__main__":
    main()
