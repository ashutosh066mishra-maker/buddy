import asyncio
from fastapi.testclient import TestClient
from main import app
from rag_engine import rag_engine_instance
import os

client = TestClient(app)

def test_rag_pipeline():
    print("Testing RAG pipeline setup...")
    
    # 1. Check if the environment variables are loaded
    assert os.environ.get("GEMINI_API_KEY") is not None, "GEMINI_API_KEY is not set."
    print("✓ Environment loaded.")
    
    # 2. Mock a PDF upload
    # We will just write a tiny dummy PDF content and let pdfplumber try to read it.
    # Actually, pdfplumber needs a valid PDF byte string. We can use reportlab to make one or just ingest pure text for testing via the RAG engine manually if we don't want to deal with valid PDF binary generation.
    # Instead, we'll manually test the `query` logic to ensure the prompt constructs successfully and the LLM responds.
    print("Testing query on empty DB (should return a notice)...")
    res = rag_engine_instance.query("What is the company's revenue?")
    assert "No documents have been ingested yet" in res or "Error" in res, "Should handle empty db."
    print("✓ Empty DB query handled.")
    
    # We will fake an ingested document
    print("Faking an ingested document...")
    chunks = ["The company reported a record revenue of $100 billion in the fiscal year 2023. This is on page 5 of the 10-K."]
    metadatas = [{"source": "mock_10k.pdf", "page": 5}]
    
    from langchain_community.vectorstores import Chroma
    from rag_engine import embeddings
    
    rag_engine_instance.vector_store = Chroma.from_texts(
        texts=chunks,
        embedding=embeddings,
        metadatas=metadatas,
        persist_directory="./chroma_db_test"
    )
    print("✓ Document faked.")
    
    # 3. Test a query
    print("Querying the RAG engine...")
    answer = rag_engine_instance.query("What was the reported revenue for 2023?")
    print(f"LLM Answer: {answer}")
    assert "100" in answer or "billion" in answer, "LLM should mention the revenue."
    assert "5" in answer or "page" in answer.lower() or "source" in answer.lower(), "LLM should cite the source/page."
    print("✓ Query successfully retrieved context and cited sources.")
    
if __name__ == "__main__":
    test_rag_pipeline()
    print("All internal self-tests passed!")
