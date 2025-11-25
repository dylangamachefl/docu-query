import streamlit as st


def get_chat_history_text(messages, doc_name):
    """Formats chat history for text file download."""
    from datetime import datetime

    header = f"Chat History for: {doc_name}\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    separator = "─" * 80 + "\n"

    chat_text = header + separator

    user_messages = [msg for msg in messages if msg["role"] == "user"]
    assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]

    for user_msg, assistant_msg in zip(user_messages, assistant_messages[1:]):
        chat_text += f"Q: {user_msg['content']}\n"
        chat_text += f"A: {assistant_msg['content']}\n\n"

    return chat_text


def show_sidebar():
    """Displays the sidebar, handles settings, and returns the configuration."""
    with st.sidebar:
        st.header("⚙️ Settings")

        st.subheader("Processing Options")

        # --- FIX: Use the 'key' parameter for direct state management ---
        st.toggle(
            "Enable Manual Chunking",
            key="manual_mode",  # This automatically updates st.session_state.manual_mode
            help="Switch to manual mode to set your own chunk size and overlap. Automatic is recommended.",
        )

        # Read the processing mode directly from session state
        processing_mode = "Manual" if st.session_state.manual_mode else "Automatic"

        chunk_size = st.session_state.get("chunk_size", 1000)
        chunk_overlap = st.session_state.get("chunk_overlap", 200)

        # --- Conditional UI now reads directly from session state ---
        if st.session_state.manual_mode:
            chunk_size = st.slider("Chunk Size", 100, 2000, chunk_size, 100)
            chunk_overlap = st.slider("Chunk Overlap", 0, 500, chunk_overlap, 50)

            st.markdown("---")

            is_doc_processed = st.session_state.get("document_processed")
            if st.button(
                "Apply & Reprocess Document",
                use_container_width=True,
                disabled=not is_doc_processed,
                type="primary",
                help="Apply the manual chunking settings to the loaded document.",
            ):
                st.session_state.chunk_size = chunk_size
                st.session_state.chunk_overlap = chunk_overlap
                st.session_state.trigger_reprocess = True
                st.toast("Settings applied! Reprocessing...", icon="⚙️")
                st.rerun()

        if st.button("Save Settings", use_container_width=True):
            st.session_state.chunk_size = chunk_size
            st.session_state.chunk_overlap = chunk_overlap
            st.toast("Settings saved!", icon="✅")

        st.divider()
        st.subheader("Actions")

        is_chat_started = len(st.session_state.get("messages", [])) > 1

        if st.button(
            "Clear Chat", use_container_width=True, disabled=not is_chat_started
        ):
            doc_name = st.session_state.get(
                "uploaded_file_name", "the current document"
            )
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": f"Chat cleared! Ask a new question about '{doc_name}'.",
                }
            ]
            st.rerun()

        st.download_button(
            label="Download Chat History",
            data=get_chat_history_text(
                st.session_state.get("messages", []),
                st.session_state.get("uploaded_file_name", "document"),
            ),
            file_name=f"chat_history_{st.session_state.get('uploaded_file_name', 'session')}.txt",
            mime="text/plain",
            use_container_width=True,
            disabled=not is_chat_started,
        )

    return processing_mode, chunk_size, chunk_overlap
