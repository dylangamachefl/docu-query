import streamlit as st


def get_chat_history_text(messages, doc_name):
    """Formats chat history for text file download."""
    from datetime import datetime

    header = f"Chat History for: {doc_name}\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    separator = "─" * 80 + "\n"

    chat_text = header + separator

    user_messages = [msg for msg in messages if msg["role"] == "user"]
    assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]

    # Start from index 1 for assistant to skip the initial greeting
    for user_msg, assistant_msg in zip(user_messages, assistant_messages[1:]):
        chat_text += f"Q: {user_msg['content']}\n"
        chat_text += f"A: {assistant_msg['content']}\n\n"

    return chat_text


def show_sidebar():
    """Displays the sidebar with settings and returns them."""
    with st.sidebar:
        st.header("⚙️ Settings")
        api_key = st.text_input(
            "Google Gemini API Key",
            type="password",
            help="Get your free API key from [Google AI Studio](https://aistudio.google.com/app/apikey).",
            value=st.session_state.get("api_key", ""),
        )

        st.subheader("Processing Options")
        manual_mode = st.toggle(
            "Enable Manual Chunking",
            value=False,
            help="Switch to manual mode to set your own chunk size and overlap.",
        )

        processing_mode = "Manual" if manual_mode else "Automatic"
        chunk_size = st.session_state.get("chunk_size", 1000)
        chunk_overlap = st.session_state.get("chunk_overlap", 200)

        if manual_mode:
            chunk_size = st.slider("Chunk Size", 100, 2000, chunk_size, 100)
            chunk_overlap = st.slider("Chunk Overlap", 0, 500, chunk_overlap, 50)

        if st.button("Save Settings", use_container_width=True, type="primary"):
            st.session_state.api_key = api_key
            st.session_state.chunk_size = chunk_size
            st.session_state.chunk_overlap = chunk_overlap
            st.toast("Settings saved!", icon="✅")

        st.divider()

        # --- NEW: Actions Section ---
        st.subheader("Actions")

        # Check if a conversation has started (more than the initial message)
        is_chat_started = len(st.session_state.get("messages", [])) > 1

        # The new Clear Chat button
        if st.button(
            "Clear Chat", use_container_width=True, disabled=not is_chat_started
        ):
            # Reset the messages to the initial state
            doc_name = st.session_state.get(
                "uploaded_file_name", "the current document"
            )
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": f"Chat cleared! Ask a new question about '{doc_name}'.",
                }
            ]
            st.rerun()  # Rerun the app to reflect the change immediately

        # The existing Download Chat History button
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

    return api_key, processing_mode, chunk_size, chunk_overlap
