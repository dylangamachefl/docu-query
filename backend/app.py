from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import tempfile
import os
import json
import logging
from logic.rag_core import (
    create_conversational_rag_chain,
    create_structured_extraction_chain,
    load_document,
    auto_select_chunk_size,
)
from guardrails import create_pii_guardrail, redact_pii_in_text
from langchain_core.messages import HumanMessage, AIMessage
from schemas import Invoice, ExtractionRequest

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
extraction_chain_cache = {}
context_cache = {}


def format_chat_history(messages: List[dict]):
    """Formats chat history for LangChain by converting dicts to message objects."""
    history = []
    for msg in messages:
        if msg["role"] == "user":
            history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            history.append(AIMessage(content=msg["content"]))
    return history


@app.post("/extract_data", response_model=Invoice)
async def extract_data(request: ExtractionRequest):
    """
    Handles a data extraction request and returns structured data.
    """
    cache_key = request.uploaded_file_name
    if cache_key not in extraction_chain_cache:
        raise HTTPException(status_code=404, detail="Extraction chain not found for this document.")

    try:
        extraction_chain = extraction_chain_cache[cache_key]
        response = await extraction_chain.ainvoke({"input": request.input_text})

        # The actual extracted data is nested under the 'answer' key
        # and needs to be returned as a dictionary to be validated by the Invoice model.
        structured_data = response.get("answer", {})
        return structured_data

    except Exception as e:
        logging.error(f"Error during data extraction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream_chat")
async def stream_chat(request: QueryRequest):
    """
    Handles a user query and streams the response back token by token.
    """
    cache_key = request.uploaded_file_name
    if cache_key not in rag_chain_cache:
        raise HTTPException(status_code=404, detail="Document not found. Please upload the document first.")

    async def stream_generator():
        try:
            # Redact PII from the user's input
            redacted_input = redact_pii_in_text(request.input_text, analyzer, anonymizer)
            rag_chain = rag_chain_cache[cache_key]
            chat_history = format_chat_history(request.chat_history) if request.chat_history else []

            # Use astream for async streaming
            async for chunk in rag_chain.astream(
                {"input": redacted_input, "chat_history": chat_history}
            ):
                if "answer" in chunk:
                    yield chunk["answer"]
                if "context" in chunk:
                    context_cache[cache_key] = chunk["context"]
        except Exception as e:
            logging.error(f"Error during streaming: {e}")

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@app.get("/get_sources/{file_name}")
async def get_sources(file_name: str):
    """
    Returns the sources for the last query for a given file.
    """
    sources = context_cache.get(file_name, [])
    return [{"page_content": doc.page_content, "metadata": doc.metadata} for doc in sources]


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
        extraction_chain = create_structured_extraction_chain(documents, api_key)

        # Cache the chains
        rag_chain_cache[file.filename] = rag_chain
        extraction_chain_cache[file.filename] = extraction_chain

        os.remove(tmp_file_path)

        return {"status": "success", "message": f"Document '{file.filename}' processed and ready."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"status": "DocuQuery backend is running."}
