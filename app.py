"""
app.py

Gradio web UI for the UIC Unofficial Course Guide RAG system.

Usage:
    python app.py
    Then open http://localhost:7860

Dependencies:
    pip install gradio>=6.9.0
"""

import gradio as gr
from query import ask

# ── Handler ───────────────────────────────────────────────────────────────────

def handle_query(question: str):
    if not question.strip():
        return "Please enter a question.", ""

    result  = ask(question)
    answer  = result["answer"]
    sources = "\n".join(f"• {s}" for s in result["sources"])

    if not sources:
        sources = "No sources retrieved."

    return answer, sources


# ── Example questions ─────────────────────────────────────────────────────────

EXAMPLES = [
    "What are the prerequisites for CS 342?",
    "Which professor is best for STAT 381?",
    "Who teaches CS 141?",
    "What is the description of IDS 435?",
    "Do students like CS 480?",
    "What do students say about workload in CS 480?",
    "Is CS 342 hard?",
    "How many credits is MATH 180?",
]

# ── UI ────────────────────────────────────────────────────────────────────────

with gr.Blocks(title="UIC Unofficial Course Guide") as demo:

    gr.Markdown("""
    # 🎓 UIC Unofficial Course Guide
    Ask questions about UIC courses, professors, prerequisites, and workload.
    Answers are grounded in scraped course data — not general AI knowledge.
    """)

    with gr.Row():
        with gr.Column(scale=2):
            question_box = gr.Textbox(
                label="Your Question",
                placeholder="e.g. What are the prerequisites for CS 342?",
                lines=2,
            )
            ask_btn = gr.Button("Ask", variant="primary")

        with gr.Column(scale=1):
            gr.Markdown("**Example questions:**")
            for ex in EXAMPLES:
                gr.Button(ex, size="sm").click(
                    fn=lambda q=ex: q,
                    outputs=question_box,
                )

    with gr.Row():
        answer_box = gr.Textbox(
            label="Answer",
            lines=8,
            interactive=False,
        )

    with gr.Row():
        sources_box = gr.Textbox(
            label="Retrieved From",
            lines=4,
            interactive=False,
        )

    # Wire up interactions
    ask_btn.click(
        fn=handle_query,
        inputs=question_box,
        outputs=[answer_box, sources_box],
    )
    question_box.submit(
        fn=handle_query,
        inputs=question_box,
        outputs=[answer_box, sources_box],
    )

    gr.Markdown("""
    ---
    *Data sources: UIC Course Catalog, Coursicle, UIC Grades, Uloop, Professor Pages*
    """)


if __name__ == "__main__":
    demo.launch()