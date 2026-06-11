"""
rag_pipeline.py

Ingestion + retrieval pipeline for the UIC Unofficial Guide RAG system.

Steps:
    1. Load all JSON data sources
    2. Extract + preprocess text per source
    3. Chunk (800 chars, 200 overlap)
    4. Embed with all-MiniLM-L6-v2
    5. Store in ChromaDB with source metadata
    6. Expose a retrieval function for querying

Usage:
    python rag_pipeline.py            # builds/rebuilds the vector store
    from rag_pipeline import retrieve  # import retrieval into other scripts

Dependencies:
    pip install sentence-transformers chromadb
"""

import json
import re
import os
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb

# ── Config ────────────────────────────────────────────────────────────────────

CHUNK_SIZE    = 800   # characters
CHUNK_OVERLAP = 200   # characters
TOP_K         = 5     # default retrieval count
DB_PATH       = "./chroma_db"
COLLECTION    = "uic_guide"

# JSON files to ingest — keys map to a short source label used in metadata
DATA_SOURCES = {
    "catalog":     "catalog_courses.json",
    "coursicle":   "coursicle_data.json",
    "reddit":      "reddit_data.json",
    "uloop":       "uloop_professors.json",
    "grades":      "uicgrades_data.json",
    "professor":   "professor_data.json",
    "easy":        "easy_courses_data.json",
    "catalog_static": "catalog_static_data.json",
}

# ── Preprocessing ─────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Strip HTML tags, normalize whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)          # strip HTML tags
    text = re.sub(r"http\S+", "", text)            # remove URLs
    text = re.sub(r"[ \t]+", " ", text)            # collapse spaces/tabs
    text = re.sub(r"\n{3,}", "\n\n", text)         # collapse excess newlines
    return text.strip()


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping character-level chunks.
    Returns list of chunk strings.
    """
    chunks = []
    start  = 0
    while start < len(text):
        end   = start + size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap  # step forward by (size - overlap)
    return chunks


# ── Text extractors per source type ──────────────────────────────────────────

def extract_texts(source_label: str, data: dict) -> list[dict]:
    """
    Given a loaded JSON dict, return a list of:
        {"text": str, "doc_id": str, "source": str}
    Each entry will be chunked independently.
    """
    docs = []

    if source_label == "catalog":
        # {"catalog_CS111": "CS 111. Program Design I. 3 hours.\n..."}
        # {"catalog_DS_BS": "DEGREE: DS_BS\n..."}
        # Values are plain text strings — chunk each entry directly.
        for key, text in data.items():
            if isinstance(text, str) and text.strip():
                docs.append({"text": text, "doc_id": key, "source": "catalog"})

    elif source_label == "catalog_static":
        # Same shape as catalog — plain text strings per degree/page block.
        for key, text in data.items():
            if isinstance(text, str) and text.strip():
                docs.append({"text": text, "doc_id": key, "source": "catalog_static"})

    elif source_label == "easy":
        # {"easy_courses_CS111": "<full dept ranking list as one string>"}
        # All keys for the same dept (easy_courses_CS111, easy_courses_CS251 etc.)
        # hold the same full dept ranking -- keep only the first entry per dept prefix.
        seen_depts = set()
        for key, text in data.items():
            if isinstance(text, str) and text.strip():
                dept_match = re.match(r"easy_courses_([A-Z]+)", key)
                dept       = dept_match.group(1) if dept_match else key
                if dept not in seen_depts:
                    seen_depts.add(dept)
                    docs.append({"text": text, "doc_id": f"easy_{dept}", "source": "easy"})

    elif source_label == "grades":
        # {"grades_CS342_FA25_Instructor:_Ayala_Rodriguez":
        #    "FA25: Software Design with Ayala, Rodriguez\n  A: 87 students\n..."}
        # Plain text per section — chunk each directly.
        for key, text in data.items():
            if isinstance(text, str) and text.strip():
                docs.append({"text": text, "doc_id": key, "source": "grades"})

    elif source_label == "professor":
        # {"professor_David_Hayes": "Professor: David Hayes\n...<classes taught>..."}
        # Plain text blob per professor — chunk directly.
        for key, text in data.items():
            if isinstance(text, str) and text.strip():
                docs.append({"text": text, "doc_id": key, "source": "professor"})

    elif source_label == "coursicle":
        # {"coursicle_CS251": {"description": "...", "professor_reviews": [...], ...}}
        for key, course in data.items():
            if not isinstance(course, dict):
                continue
            parts = []
            code = course.get("course_code", key.replace("coursicle_", ""))
            parts.append(f"Course: {code}")
            if course.get("description"):
                parts.append(f"Description: {course['description']}")
            if course.get("avg_rating"):
                parts.append(f"Average professor rating: {course['avg_rating']}")
            if course.get("credits"):
                parts.append(f"Credits: {course['credits']}")
            if course.get("class_size"):
                parts.append(f"Class size: {course['class_size']}")
            if course.get("usually_offered"):
                parts.append(f"Usually offered: {course['usually_offered']}")
            if course.get("recent_professors"):
                parts.append(f"Recent professors: {course['recent_professors']}")
            for rev in course.get("professor_reviews", []):
                body = rev.get("body", "").strip()
                if body:
                    author = rev.get("author", "Anonymous")
                    year   = rev.get("year", "")
                    major  = rev.get("major", "")
                    parts.append(f"Student review ({year} {major}, {author}): {body}")
            if parts:
                docs.append({
                    "text":   "\n".join(parts),
                    "doc_id": key,
                    "source": "coursicle",
                })

    elif source_label == "reddit":
        # {"reddit_CS251": {"posts": [{"title": ..., "comments": [...]}]}}
        for key, course in data.items():
            if not isinstance(course, dict):
                continue
            for post in course.get("posts", []):
                title    = post.get("title", "")
                comments = post.get("comments", [])
                combined = f"Post: {title}\n" + "\n".join(comments)
                if combined.strip():
                    docs.append({
                        "text":   combined,
                        "doc_id": f"{key}_{post.get('url', '')[-20:]}",
                        "source": "reddit",
                    })

    elif source_label == "uloop":
        # {"uloop_Mitchell Theys": {"department": ..., "reviews": [{"comment": ...}]}}
        for key, prof in data.items():
            if not isinstance(prof, dict):
                continue
            name = prof.get("name", key.replace("uloop_", ""))
            parts = [f"Professor: {name}"]
            if prof.get("department"):
                parts.append(f"Department: {prof['department']}")
            if prof.get("rating"):
                parts.append(f"Overall listing rating: {prof['rating']}/5")
            for rev in prof.get("reviews", []):
                comment = rev.get("comment", "").strip()
                if comment:
                    overall = rev.get("overall", "?")
                    parts.append(
                        f"Review (overall={overall}/5, "
                        f"helpfulness={rev.get('helpfulness', '?')}/5, "
                        f"clarity={rev.get('clarity', '?')}/5, "
                        f"easiness={rev.get('easiness', '?')}/5): {comment}"
                    )
            if len(parts) > 1:
                docs.append({
                    "text":   "\n".join(parts),
                    "doc_id": key,
                    "source": "uloop",
                })

    return docs


# ── Build vector store ────────────────────────────────────────────────────────

def build_vector_store():
    print("🔧 Loading embedding model (all-MiniLM-L6-v2)…")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print(f"🗄️  Initializing ChromaDB at {DB_PATH}…")
    client     = chromadb.PersistentClient(path=DB_PATH)

    # Delete existing collection so rebuilds are clean
    try:
        client.delete_collection(COLLECTION)
        print(f"   ♻️  Dropped existing '{COLLECTION}' collection")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    all_ids        = []
    all_embeddings = []
    all_documents  = []
    all_metadatas  = []

    total_chunks = 0

    for source_label, filename in DATA_SOURCES.items():
        path = Path(filename)
        if not path.exists():
            print(f"   ⚠️  {filename} not found — skipping")
            continue

        print(f"\n📄 Processing {filename}…")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        docs        = extract_texts(source_label, data)
        src_chunks  = 0

        for doc in docs:
            cleaned = clean_text(doc["text"])
            chunks  = chunk_text(cleaned)

            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc['doc_id']}__chunk{i}"
                embedding = model.encode(chunk).tolist()

                all_ids.append(chunk_id)
                all_embeddings.append(embedding)
                all_documents.append(chunk)
                all_metadatas.append({
                    "source":   doc["source"],
                    "doc_id":   doc["doc_id"],
                    "chunk_idx": i,
                    "filename": filename,
                })
                src_chunks += 1

        total_chunks += src_chunks
        print(f"   ✅ {len(docs)} docs → {src_chunks} chunks")

    # Batch upsert into ChromaDB (max 5000 per call to stay safe)
    print(f"\n⬆️  Uploading {total_chunks} chunks to ChromaDB…")
    batch_size = 2000
    for start in range(0, len(all_ids), batch_size):
        end = start + batch_size
        collection.add(
            ids        = all_ids[start:end],
            embeddings = all_embeddings[start:end],
            documents  = all_documents[start:end],
            metadatas  = all_metadatas[start:end],
        )
        print(f"   Uploaded chunks {start}–{min(end, len(all_ids))}")

    print(f"\n{'='*60}")
    print(f"✅ Vector store built: {total_chunks} total chunks")
    print(f"{'='*60}\n")
    return model, collection


# ── Retrieval ─────────────────────────────────────────────────────────────────

def load_retriever():
    """Load embedding model + existing ChromaDB collection for querying."""
    model      = SentenceTransformer("all-MiniLM-L6-v2")
    client     = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_collection(COLLECTION)
    return model, collection


def retrieve(query: str, k: int = TOP_K, model=None, collection=None) -> list[dict]:
    """
    Embed query, retrieve top-k chunks from ChromaDB.

    Returns list of dicts:
        {
            "text":      str,   # chunk text
            "source":    str,   # e.g. "catalog", "reddit"
            "doc_id":    str,   # e.g. "catalog_CS251"
            "chunk_idx": int,   # position within source doc
            "score":     float, # cosine distance (lower = more similar)
        }
    """
    if model is None or collection is None:
        model, collection = load_retriever()

    query_embedding = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for text, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text":      text,
            "source":    meta["source"],
            "doc_id":    meta["doc_id"],
            "chunk_idx": meta["chunk_idx"],
            "score":     round(dist, 4),
        })

    return chunks


# ── CLI entrypoint ────────────────────────────────────────────────────────────

def main():
    model, collection = build_vector_store()

    # Quick retrieval smoke test
    test_queries = [
        "Which professor is best for STAT 381?",
        "What are the prerequisites for CS251?",
        "Who teaches CS251?",
        "What skills will I learn in IDS 435?",
        "What do current students say about workload in CS480 or CS 342?",
    ]

    print("\n🔍 Smoke test — sample retrievals:\n")
    for query in test_queries:
        print(f"  Query: \"{query}\"")
        results = retrieve(query, k=TOP_K, model=model, collection=collection)
        for r in results:
            preview = r["text"][:120].replace("\n", " ")
            print(f"    [{r['source']} / {r['doc_id']} / chunk {r['chunk_idx']} / score {r['score']}]")
            print(f"    {preview}…")
        print()

    # print("\n🔍 Diagnostic — all doc_ids in DB:\n")
    # all_meta = collection.get(include=["metadatas"])
    # doc_ids = sorted(set(m["doc_id"] for m in all_meta["metadatas"]))
    # for d in doc_ids:
    #     print(f"  {d}")

if __name__ == "__main__":
    main()