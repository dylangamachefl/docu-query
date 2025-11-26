from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import List, Optional
import tempfile
import os
from logic.rag_core import (
    create_conversational_rag_chain,
    load_document,
    auto_select_chunk_size,
)
from guardrails import create_pii_guardrail, redact_pii_in_text
from langchain_core.messages import HumanMessage, AIMessage

# Initialize PII guardrails
analyzer, anonymizer = create_pii_guardrail()

class QueryRequest(BaseModel):
    """Request model for a user query."""
    input_text: str = Field(..., description="The user's query text.")
    chat_history: Optional[List[dict]] = Field(None, description="Previous chat messages.")
    uploaded_file_name: str = Field(..., description="The name of the uploaded file.")
    mode: str = Field("Automatic", description="Processing mode ('Automatic' or 'Manual').")
    manual_chunk_size: int = Field(1000, description="Manual chunk size.")
    manual_chunk_overlap: int = Field(200, description="Manual chunk overlap.")

class QueryResponse(BaseModel):
    """Response model for a query."""
    answer: str
    sources: Optional[List[dict]] = None

app = FastAPI(
    title="DocuQuery Backend",
    description="Handles document processing and conversational RAG.",
    version="1.0.0",
)

# In-memory storage for RAG chains (replace with a more robust solution in production)
rag_chain_cache = {}

def format_chat_history(messages: List[dict]):
    """Formats chat history for LangChain by converting dicts to message objects."""
    history = []
    for msg in messages:
        if msg["role"] == "user":
            history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            history.append(AIMessage(content=msg["content"]))
    return history

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    try:
        # Redact PII from the user's input
        redacted_input = redact_pii_in_text(request.input_text, analyzer, anonymizer)

        # Use the uploaded file name as a key for the RAG chain
        cache_key = request.uploaded_file_name

        if cache_key not in rag_chain_cache:
            raise HTTPException(status_code=404, detail="Document not found. Please upload the document first.")

        rag_chain = rag_chain_cache[cache_key]

        chat_history = format_chat_history(request.chat_history) if request.chat_history else []

        response = rag_chain.invoke(
            {"input": redacted_input, "chat_history": chat_history}
        )

        return QueryResponse(
            answer=response.get("answer"),
            sources=[{"page_content": doc.page_content, "metadata": doc.metadata} for doc in response.get("context", [])]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    mode: str = Form("Automatic"),
    manual_chunk_size: int = Form(1000),
    manual_chunk_overlap: int = Form(200)
):
    """
    A new endpoint to handle document processing and caching the RAG chain.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            tmp_file.write(file.file.read())
            tmp_file_path = tmp_file.name

        documents = load_document(tmp_file_path)

        if mode == "Automatic":
            chunk_size, chunk_overlap = auto_select_chunk_size(documents)
        else:
            chunk_size, chunk_overlap = manual_chunk_size, manual_chunk_overlap

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not set")

        rag_chain = create_conversational_rag_chain(
            documents, api_key, chunk_size, chunk_overlap
        )

        # Cache the RAG chain
        rag_chain_cache[file.filename] = rag_chain

        os.remove(tmp_file_path)

        return {"status": "success", "message": f"Document '{file.filename}' processed and ready."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"status": "DocuQuery backend is running."}
