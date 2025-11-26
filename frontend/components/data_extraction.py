import streamlit as st
import requests
import pandas as pd

def show_extraction_ui(backend_url: str):
    """Displays the UI for the Data Extraction Mode."""
    st.markdown("### Data Extraction Mode")

    # Check if a document has been processed
    if not st.session_state.get("document_processed", False):
        st.warning("Please upload and process a document first.")
        return

    extraction_prompt = st.text_input(
        "Enter what you want to extract (e.g., 'invoice number, vendor name, total amount'):",
        key="extraction_prompt"
    )

    if st.button("Extract Data"):
        if not extraction_prompt:
            st.error("Please enter what you want to extract.")
            return

        with st.spinner("Extracting data..."):
            try:
                payload = {
                    "input_text": extraction_prompt,
                    "uploaded_file_name": st.session_state.uploaded_file_name,
                }
                response = requests.post(f"{backend_url}/extract_data", json=payload)
                response.raise_for_status()

                extracted_data = response.json()

                # Filter out None values and display the data
                filtered_data = {k: v for k, v in extracted_data.items() if v is not None}

                if not filtered_data:
                    st.info("No data was extracted for the specified fields.")
                    return

                st.success("Data extracted successfully!")

                # Convert to DataFrame for better display
                df = pd.DataFrame([filtered_data])
                st.dataframe(df)

            except requests.exceptions.RequestException as e:
                st.error(f"Error communicating with backend: {e}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")
