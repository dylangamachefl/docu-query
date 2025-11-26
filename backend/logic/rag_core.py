import os
import warnings
from typing import List, Tuple

# LangChain imports for conversational RAG
from langchain_classic.chains import create_history_aware_retriever
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate

# Core LangChain and community imports
from langchain_core.documents import Document
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

# For Hybrid Search
from langchain_community.retrievers.ensemble import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

from schemas import Invoice


warnings.filterwarnings("ignore")


def load_document(file_path: str) -> List[Document]:
    """Loads a document from a file path."""
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension == ".pdf":
        loader = PyMuPDFLoader(file_path)
    elif file_extension == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")
    elif file_extension == ".docx":
        loader = Docx2txtLoader(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")
    return loader.load()


def auto_select_chunk_size(documents: List[Document]) -> Tuple[int, int]:
    """Automatically chooses optimal chunk size and overlap based on document length."""
    full_text = "".join([doc.page_content for doc in documents])
    total_length = len(full_text)
    if total_length < 5000:
        return 500, 100
    elif total_length < 50000:
        return 1000, 200
    else:
        return 1500, 300


def split_documents(
    documents: List[Document], chunk_size: int, chunk_overlap: int
) -> List[Document]:
    """Splits documents into smaller chunks."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return text_splitter.split_documents(documents)


def create_conversational_rag_chain(
    documents: List[Document], api_key: str, chunk_size: int, chunk_overlap: int
):
    """Creates a conversational RAG chain that is aware of chat history."""
    os.environ["GOOGLE_API_KEY"] = api_key
    llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    chunks = split_documents(documents, chunk_size, chunk_overlap)
    if not chunks:
        raise ValueError("Document splitting resulted in no chunks.")

    # FAISS vector store for semantic search
    faiss_vectorstore = FAISS.from_documents(documents=chunks, embedding=embeddings)
    faiss_retriever = faiss_vectorstore.as_retriever(
        search_type="similarity", search_kwargs={"k": 4}
    )

    # BM25 retriever for keyword search
    bm25_retriever = BM25Retriever.from_documents(chunks)
    bm25_retriever.k = 4

    # Ensemble retriever to combine both methods
    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, faiss_retriever], weights=[0.5, 0.5]
    )


    # 1. Contextualize question prompt
    contextualize_q_system_prompt = (
        "Given a chat history and the latest user question "
        "which might reference context in the chat history, "
        "formulate a standalone question which can be understood "
        "without the chat history. Do NOT answer the question, "
        "just reformulate it if needed and otherwise return it as is."
    )
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    history_aware_retriever = create_history_aware_retriever(
        llm, ensemble_retriever, contextualize_q_prompt
    )

    # 2. Answering prompt
    qa_system_prompt = (
        "You are an expert assistant for question-answering tasks. "
        "Use the provided context to answer the question. "
        "If you don't know the answer, just say that you don't know. "
        "Keep the answer concise and use a maximum of three sentences.\n\n"
        "Context: {context}"
    )
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", qa_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    return rag_chain


def create_structured_extraction_chain(documents: List[Document], api_key: str):
    """Creates a chain for structured data extraction."""
    os.environ["GOOGLE_API_KEY"] = api_key
    llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = text_splitter.split_documents(documents)
    if not chunks:
        raise ValueError("Document splitting resulted in no chunks.")

    vectorstore = FAISS.from_documents(documents=chunks, embedding=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    system_prompt = (
        "You are an expert extraction agent. "
        "Your task is to extract relevant information from the provided context "
        "and format it according to the specified JSON schema. "
        "Only extract data for the fields mentioned in the user's request.\n\n"
        "Context: {context}"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )

    # Create a chain that combines document retrieval with structured output
    structured_llm = llm.with_structured_output(Invoice)
    retrieval_chain = create_retrieval_chain(
        retriever, create_stuff_documents_chain(structured_llm, prompt)
    )
    return retrieval_chain
