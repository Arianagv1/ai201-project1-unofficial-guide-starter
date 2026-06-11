# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->

I have chosen Data Science Courses for UIC DS students since it's a relatively new program in the CS department. Because of this, I would like to help UIC DS students find courses that are manageable, genuinely interesting, and well-taught, which support workload balance and mental wellness, not just degree completion. 


---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Rate my professor| Blog | https://www.ratemyprofessors.com/school/1111|
| 2 | Reddit |Blog  |https://www.reddit.com/r/uichicago/ |
| 3 | UIC catalog |School website | https://catalog.uic.edu/ucat/
| 4 | UIC grade distribution | School website | https://uicgrades.com/ |
| 5 | UIC Data Science Major Info Page| School website| https://cs.uic.edu/undergraduate/data-science-major/ |
| 6 | Coursicle | Blog | https://www.coursicle.com/uic/|
| 7 | LinkedIn UIC| Blog |https://www.linkedin.com/school/thisisuic/posts/?feedView=all |
| 8 | Medium | Blog | https://medium.com/search?q=uic|
| 9 | Student Orgs |School website | https://cs.uic.edu/undergraduate      student-organizations/|
| 10 | ULoop |Blog |https://illinois.uloop.com/professors |

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

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

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**
- all-MiniLM-L6-v2 (384 dimensions)

**Production tradeoff reflection:**
There are other models that do have fast speeds and are high quality, for example: Open AI's text embedding model 3-small would be great since its setup is simple and is great for general uses, or cohere embed-english v3.0 for production RAG systems, like this one specifically. However, they are not free. 
---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**

**How source attribution is surfaced in the response:**

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
Tier One: Happy Paths 
| 1 |What are the prereqs for CS251? | UIC Catalog chunk with full prereq list|
| 2 | Who teaches CS251?| Professors names |

Tier Two: Medium Difficulty
| 3 | Is Professor Hallenback known for being generous with grading?| RMP reviews mentioning grading |
| 4 | What skills will I learn in IDS 435? | Course description |

Tier Three: Hard Difficulty
| 5 | What do current students say about workload in CS480 or Cs 342?| Multiple Reddit/ RMP reviews synthesized |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**

**What the system returned:**

**Root cause (tied to a specific pipeline stage):**

**What you would change to fix it:**

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**

**One way your implementation diverged from the spec, and why:**

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*

**Instance 2**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*
