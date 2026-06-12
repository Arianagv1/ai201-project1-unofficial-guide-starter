# The Unofficial Guide — Project 1

---

## Domain

I have chosen Data Science Courses for UIC DS students since it's a relatively new program in the CS department. Because of this, I would like to help UIC DS students find courses that are manageable, genuinely interesting, and well-taught, which support workload balance and mental wellness, not just degree completion. 


---

## Document Sources

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | Rate my professor| Blog | https://www.ratemyprofessors.com/school/1111|
| 2 | Reddit |Blog  |https://old.reddit.com |
| 3 | UIC catalog |School website | https://catalog.uic.edu/ucat/|
| 4 | UIC grade distribution | School website | https://uicgrades.com/ |
| 5 | UIC Data Science Major Info Page| School website| https://catalog.uic.edu/ucat/colleges-depts/engineering/cs/bs-data-science-computer-science/
| 6 | Coursicle | Blog | https://www.coursicle.com/uic/|
| 7 | LinkedIn UIC| Blog |https://www.linkedin.com/school/thisisuic/posts/?feedView=all |
| 8 | UIC Easy Classes | Blog | https://uicgrades.com/findEasyCourses.html |
| 9 | Student Orgs |School website | https://cs.uic.edu/undergraduate      student-organizations/|
| 10 | ULoop |Blog |https://illinois.uloop.com/professors |

---

## Chunking Strategy

Because of the nature of my program, my two content types (school catalogs or 
blogs/reviews) its best to do a mix for chunking strategy. For example, short reviews would have a more optimal chunk size of 300-500 characters for a full review. Because splitting could lose context and tone. For long catalogs, splitting prevents overwhelming context noise, and keeping a small chunk strategy would dilute semantic relevance. 

Source Type           → Chunking Strategy
─────────────────────────────────────────
Reviews               → Full review (if <1000 chars) OR sentence-based with min context
Class descriptions    → By section header (Prerequisites, Description, Grading, etc.)
Course catalogs       → Paragraph-based, max 800 chars
Prerequisites lists   → Keep together as one chunk if ≤500 chars
GPA/policy pages      → Split by rule/policy, keep examples together


**Chunk size:**
After looking at my different sources, I have chosen an 800 char chunks strategy. This will keep prereqs/grading/descriptions intact.
**Overlap:**
I will be usig overlap of 200 characters. This prevents important concepts from falling exactly at chunk boundaries, like miss full policies about grading/prereq requirements. I also plan on using metadata filtering to help re-rank. However, this will not solve boundary fragmentation during retrieval.
**Why these choices fit your documents:**
Preprocessing removes HTML tags, navigation/ header boilerplate, and normalizes whitespace. This is applied before chunking to ensure all chunks start from clean text. Cleaner input improves embedding quality (all-MiniLM produces more accurate vectors for well-formed text).
**Final chunk count:**
The chunk count is determined by running the preprocessing + chunking pipeline on all 10 sources. Estimated range: 80–150 chunks (varies by source size). Measured via: total_chunks = sum(len(chunk_with_overlap(preprocess(source), 800, 200)) for source in sources).

- Example calculation:
  - Source 1: 8K chars → ~10 chunks
  - Source 2: 12K chars → ~15 chunks
  - ...
  - Total: ~120 chunks (example)
---

## Embedding Model

**Model used:**
- all-MiniLM-L6-v2 (384 dimensions)

**Production tradeoff reflection:**
-There are other models that do have fast speeds and are high quality, for example: Open AI's text embedding model 3-small would be great since its setup is simple and is great for general uses, or cohere embed-english v3.0 for production RAG systems, like this one specifically. However, they are not free. 
---

## Grounded Generation

**System prompt grounding instruction:**
The key engineering challenge here is that my prompt must instruct the LLM to answer from the retrieved context only, not from its general training knowledge. Without this, my system will produce confident-sounding answers that have nothing to do with my JSON documents that I intended to use for the student DS major application. 
**How source attribution is surfaced in the response:**
I instructed the LLM's response to name which document(s) the answer came from, either by instructing the model to cite sources or by appending retrieved source names programmatically after generation. 
---

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 |What are the prereqs for CS251? | UIC Catalog chunk with full prereq list| CS211, CS141 | Releveant & Accurate |
| 2 | Which professor is best for STAT 381?| Professors names or ULoop | Lia Liu recommended based on student reviews | Releveant & Accurate |
| 3 | Who teaches CS141?| UIC catalog or Professor search | Lists 9 recent professors | Releveant & Accurate |
| 4 |What is the description of IDS 435?| Course description | Optimization methods (etc) | Partially Relevant & Accurate |
| 5 | Do students like CS 480?| Multiple Reddit/ RMP reviews synthesized | Mixed but mostly negative reviews | Partially relevant & Accurate| 

---

## Failure Case Analysis

**Question that failed:**
I originally had one of my questions framed as "What skills will I learn taking IDS 435?".

**What the system returned:**
The system kept returning that it did not have enough information to produce an answer, which was a guardrail I kept as to not hallucinate answers. 

**Root cause (tied to a specific pipeline stage):**
Although I had substantial information about this course across different JSON files I scraped from catalogs, reviews on ULoop and coursicle, I believe the issue here was because the relevant information was split across a chunk boundary so retrieval only returned half the context. 

**What you would change to fix it:**
The fix would be applied at the retrieval stage. After retrieving the top-k chunks by similarity, the pipeline should automatically fetch all remaining chunks from the same source document (e.g. all chunks of `coursicle_IDS435` and `catalog_IDS435`) and append them to the context window before passing to the LLM. This ensures that if a course description is split across chunk 0 and chunk 1, the LLM sees the complete text rather than a truncated half. A secondary fix would be to increase chunk overlap from 200 to 300–400 characters specifically for short structured fields like course descriptions, reducing the likelihood of a key phrase like "skills" or "you will learn" landing exactly at a boundary.

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**
Using planning.md during production helped me understand a lot of new terminology- chunks, scraping, each crucial step of the entire LLM and retrieval process, and gave me new insights on the RAG implementation. I learned a lot about how to create a good JSON file and I also learned about the skills it took to make sure that the resources I had were balanced in structured and unstructured formats from catalogs to reviews, and the different chunking approaches I would need to evaluate for each one. I also appreciated being able to debug each step at a time since I spent a lot of time outlining each one.

**One way your implementation diverged from the spec, and why:**
My original spec planned to use RateMyProfessors and the official Reddit API as two of my unstructured opinion sources. During implementation, RateMyProfessors was intermittently down and Reddit's app registration process blocked API access, so I pivoted to scraping `old.reddit.com` directly using `requests` and `BeautifulSoup`, and replaced RateMyProfessors with Uloop — a student review platform specific to UIC. This actually improved the quality of the unstructured data since Uloop reviews are UIC-specific and include structured sub-ratings (helpfulness, clarity, easiness) alongside free-text comments, making them more useful for RAG retrieval than the more generic RateMyProfessors format.

---

## AI Usage

**Instance 1**
- *What I gave the AI:* My LLM system prompt and a set of failing query outputs showing the model returning "I don't have enough information" even when the retrieved chunks clearly contained the answer.
- *What it produced:* A diagnosis identifying that the instruction "Do NOT use your general training knowledge" was being interpreted too conservatively by the model, causing it to refuse synthesis even from the provided context. It rewrote the system prompt with softer grounding rules and added explicit instructions telling the model where to look for prerequisites and professor names within the chunk text.
- *What I changed or overrode:* I retained the strict fallback response ("I don't have enough information on that based on the available course data.") as a hard guardrail for genuinely unanswerable queries, and kept `temperature=0.1` rather than raising it — prioritizing faithfulness to the retrieved context over fluency, which is the correct tradeoff for a grounded RAG system.


**Instance 2**
- *What I gave the AI:* Sample entries from each of my five JSON files (`catalog_courses.json`, `uicgrades_data.json`, `easy_courses_data.json`, `professor_data.json`, `uloop_professors.json`) alongside the ingestion pipeline that was producing empty or incorrect chunks.
- *What it produced:* A rewritten `extract_texts()` function with a dedicated extractor branch for each source, matched precisely to the actual key structure and value format of each JSON. Notably it identified that `easy_courses_data.json` stored the entire department ranking list under every course key, causing duplicate chunk IDs in ChromaDB, and fixed it by deduplicating on department prefix rather than text content.
- *What I changed or overrode:* I directed the AI to verify each extractor against the real JSON samples I provided rather than inferring structure from the scraper code alone — catching mismatches that would have silently produced empty embeddings without any error message, which is a particularly subtle failure mode in RAG pipelines.

## Demo

https://app.screencastify.com/watch/KfbMFnBumKKQPAwCm3wL
