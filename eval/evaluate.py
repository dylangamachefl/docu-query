import os
import sys
import asyncio
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import context_precision, faithfulness
from langchain_core.documents import Document

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.logic.rag_core import create_conversational_rag_chain

# --- Golden Dataset ---
# In a real-world scenario, this would be a carefully curated dataset.
golden_dataset = {
    'question': [
        "What is the capital of France?",
        "Who wrote 'To Kill a Mockingbird'?",
    ],
    'ground_truth': [
        "The capital of France is Paris.",
        "Harper Lee wrote 'To Kill a Mockingbird'.",
    ],
}

def create_dummy_documents():
    """Creates a dummy document set for the RAG chain."""
    return [
        Document(page_content="France's capital is Paris, a major European city."),
        Document(page_content="Harper Lee, an American novelist, is famous for her book 'To Kill a Mockingbird'."),
    ]

async def run_evaluation():
    """Runs the RAGas evaluation pipeline."""
    # 1. Setup the RAG chain
    # Ensure you have a GOOGLE_API_KEY set in your environment
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")

    documents = create_dummy_documents()
    rag_chain = create_conversational_rag_chain(documents, api_key, 1000, 200)

    # 2. Prepare the dataset for Ragas
    questions = golden_dataset['question']
    ground_truths = [[gt] for gt in golden_dataset['ground_truth']] # Ragas expects a list of ground truths

    # 3. Generate answers and contexts from the RAG chain
    answers = []
    contexts = []

    for question in questions:
        response = rag_chain.invoke({"input": question, "chat_history": []})
        answers.append(response.get("answer", ""))
        contexts.append([doc.page_content for doc in response.get("context", [])])

    # 4. Create a Hugging Face Dataset
    dataset_dict = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    }
    dataset = Dataset.from_dict(dataset_dict)

    # 5. Evaluate the RAG pipeline
    result = evaluate(
        dataset=dataset,
        metrics=[context_precision, faithfulness],
    )

    print("--- RAG Evaluation Results ---")
    print(result)
    print("-----------------------------")

if __name__ == "__main__":
    # Note: Ragas evaluation is async
    asyncio.run(run_evaluation())
