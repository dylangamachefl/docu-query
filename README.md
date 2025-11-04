# 📄 DocuQuery: Your Conversational Document Assistant

**DocuQuery** is an intelligent, conversational assistant that allows you to chat with your documents. Go beyond simple Q&A; engage in a natural, context-aware dialogue about your PDFs, Word documents, and text files.

This application leverages a sophisticated Retrieval-Augmented Generation (RAG) pipeline, powered by Google's Gemini models and orchestrated by LangChain, to provide answers that are not only accurate but also grounded in the document's content.

**(Strongly recommend creating a short GIF of the app in action and placing it here!)**


---

## ✨ Key Features

*   **🧠 Truly Conversational & Context-Aware**: Remembers the flow of your conversation. Ask follow-up questions, use pronouns, and interact naturally, just like you would with a human expert.
*   **🎯 History-Aware Retrieval**: Intelligently rewrites your follow-up questions behind the scenes into detailed, standalone queries. This ensures the most relevant information is retrieved every single time.
*   **🤖 Smart Processing Modes**: Features an **Automatic** mode that analyzes your document and chooses the optimal processing settings. For power users, a **Manual** mode provides full control over text chunking parameters.
*   **🔍 Source-Backed Answers**: Never guess where information comes from. Every answer is accompanied by an expandable "View Sources" section, showing the exact snippets from the document used for generation.
*   **📂 Multi-Format Support**: Natively handles `.pdf`, `.docx`, and `.txt` files.
*   **🛠️ Session Management**:
    *   **Clear Chat**: Easily start a new conversation about the same document.
    *   **Download History**: Export your entire chat session as a `.txt` file for your records.
*   **🎨 Modern & Responsive UI**: A clean, intuitive, and professionally styled interface built with Streamlit.

---

## 🤔 How It Works

The application follows a two-stage process to provide a seamless experience:

1.  **One-Time Processing (On Upload)**: When you upload a document, the system performs the heavy lifting upfront.
    *   **Loads & Chunks**: The document is loaded and split into small, manageable chunks of text.
    *   **Embeds & Indexes**: Each chunk is converted into a numerical representation (an embedding) that captures its semantic meaning. These embeddings are stored in a highly efficient, in-memory FAISS vector store.
    *   This entire process happens **only once per document**, ensuring subsequent interactions are fast.

2.  **Conversational Loop (Per Question)**:
    *   Your new question is combined with the chat history.
    *   An LLM rewrites this into a detailed, standalone question.
    *   This rewritten question is used to find the most relevant chunks from the vector store.
    *   The LLM receives the original question, chat history, and the retrieved chunks to generate a final, context-aware answer.

*A note on file size: The default maximum upload size is 200MB, a limit set by Streamlit to ensure app stability on common hosting platforms with limited memory.*

---

## 🛠️ Tech Stack

*   **Framework**: Streamlit
*   **Language Model & Embeddings**: Google Gemini API (`gemini-2.5-flash`)
*   **Core Orchestration**: LangChain (featuring `create_history_aware_retriever`)
*   **Vector Store**: FAISS (Facebook AI Similarity Search) for in-memory vector indexing
*   **Document Loaders**: `PyPDF`, `python-docx`

---

## 🚀 Getting Started

Follow these steps to get DocuQuery running on your local machine.

### 1. Prerequisites

*   Python 3.8 - 3.11
*   An active **Google Gemini API Key**. You can get a free key from [Google AI Studio](https://aistudio.google.com/app/apikey).

### 2. Clone the Repository & Set Up Environment

First, clone the project repository and create a virtual environment.

```bash
git clone https://github.com/your-username/docuquery.git
cd docuquery

# Create a virtual environment
python -m venv venv

# Activate the environment
# On Windows:
.\venv\Scripts\Activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

Install all the required Python packages using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 4. Running the Application

Launch the Streamlit application with a single command:

```bash
streamlit run app.py
```

Your web browser should automatically open to the application. To start using it:
1.  Navigate to the **Settings** sidebar.
2.  Enter your **Google Gemini API Key**.
3.  Click **"Save Settings"**.
4.  Upload a document and start your conversation!

---

## 📂 Project Structure

The project is organized into modular components for clarity and scalability:

```
docuquery/
├── .streamlit/
│   └── config.toml      # Streamlit theme configuration
├── assets/
│   └── styles.css       # Custom CSS for UI styling
├── components/
│   └── sidebar.py       # UI components for the sidebar
├── core/
│   └── rag_core.py      # Core RAG logic and processing
├── app.py               # Main Streamlit application file
├── requirements.txt     # Project dependencies
└── README.md            # You are here!
```

---

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.