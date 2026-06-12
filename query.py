"""
query.py

End-to-end RAG query function:
    1. Embed the user question with all-MiniLM-L6-v2
    2. Retrieve top-k chunks from ChromaDB
    3. Pass chunks as context to Groq llama-3.3-70b-versatile
    4. Return grounded answer + source list

Usage:
    from query import ask
    result = ask("What are the prerequisites for CS 342?")
    print(result["answer"])
    print(result["sources"])
"""

import os
from dotenv import load_dotenv
from groq import Groq
from rag_pipeline import load_retriever, retrieve

load_dotenv()

# ── Clients ───────────────────────────────────────────────────────────────────

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Load embedding model + ChromaDB once at import time so app.py reuses them
_model, _collection = load_retriever()

# ── Prompt template ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an academic advisor assistant for UIC (University of Illinois Chicago).
You answer questions about courses, professors, and academic requirements.

RULES:
1. Answer using ONLY the information in the provided documents. Read them carefully and extract all relevant details.
2. You MUST answer if the documents contain the relevant information — even if it is partial.
3. Only say "I don't have enough information on that based on the available course data." if the documents genuinely contain NO relevant information at all.
4. Do not add facts from outside the documents (no general knowledge about UIC or courses).
5. Cite naturally (e.g. "According to the course catalog...", "The Coursicle page lists...", "Student reviews note...").
6. Keep your answer concise and directly address the question.
7. For prerequisites, look for phrases like "Prerequisite(s):" in the documents and quote them directly.
8. For who teaches a course, look for "Recent Professors" or professor names listed in the documents."""

def build_user_prompt(question: str, chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered document list for the LLM."""
    doc_lines = []
    for i, chunk in enumerate(chunks, 1):
        source_label = f"[Document {i} — source: {chunk['source']}, id: {chunk['doc_id']}]"
        doc_lines.append(f"{source_label}\n{chunk['text']}")

    docs_block = "\n\n---\n\n".join(doc_lines)

    return f"""Here are the retrieved documents:

{docs_block}

---

Question: {question}

Answer using only the documents above. If they don't contain the answer, say so."""


# ── Main ask function ─────────────────────────────────────────────────────────

def ask(question: str, k: int = 5) -> dict:
    """
    Full RAG pipeline: retrieve → generate → return.

    Returns:
        {
            "answer":  str,
            "sources": list[str],   # deduped source labels
            "chunks":  list[dict],  # raw retrieved chunks for inspection
        }
    """
    # Step 1: Retrieve
    chunks = retrieve(question, k=k, model=_model, collection=_collection)

    # If the top result is the exact course, also pull its other chunks
    # so prereq text (often in chunk 1+) isn't missed
    top_doc_id = chunks[0]['doc_id'] if chunks else None
    if top_doc_id:
        extra = _collection.get(
            where={"doc_id": {"$eq": top_doc_id}},
            include=["documents", "metadatas"],
        )
        for doc, meta in zip(extra["documents"], extra["metadatas"]):
            already = any(c["doc_id"] == meta["doc_id"] and c["chunk_idx"] == meta["chunk_idx"] for c in chunks)
            if not already:
                chunks.append({"text": doc, "source": meta["source"], "doc_id": meta["doc_id"], "chunk_idx": meta["chunk_idx"], "score": 0.0})

    if not chunks:
        return {
            "answer":  "I don't have enough information on that based on the available course data.",
            "sources": [],
            "chunks":  [],
        }

    # Step 2: Build prompt
    user_prompt = build_user_prompt(question, chunks)

    # Step 3: Generate with Groq
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.1,   # low temp = more faithful to context
        max_tokens=512,
    )

    answer = response.choices[0].message.content.strip()

    # Step 4: Build source list (deduplicated, human-readable)
    seen    = set()
    sources = []
    for chunk in chunks:
        label = f"{chunk['source']} — {chunk['doc_id']}"
        if label not in seen:
            seen.add(label)
            sources.append(label)

    return {
        "answer":  answer,
        "sources": sources,
        "chunks":  chunks,
    }


# ── CLI smoke test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_queries = [
        "Which professor is best for STAT 381?", #works fine!
        "What are the prerequisites for CS 342?", 
        "Who teaches CS 141?",
        "What is the description of IDS 435?",
        "Do students like CS 480?",
    ]

    print("=" * 60)
    print("RAG Grounded Generation — Smoke Test")
    print("=" * 60)

    for q in test_queries:
        print(f"\nQ: {q}")
        result = ask(q)
        print(f"A: {result['answer']}")
        print("Sources:")
        for s in result["sources"]:
            print(f"  • {s}")
        print("-" * 60)