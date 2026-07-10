def build_rag_prompt(context: str, question: str) -> str:
    return (
        "You are a helpful assistant. Use the provided context from the user's documents to answer the question. "
        "If the document content does not contain an answer, say you do not know."
        f"\n\nContext:\n{context}\n\nQuestion: {question}"
    )


def build_summary_prompt(text: str) -> str:
    return (
        "Summarize the following text in concise bullet points while preserving meaning and technical details."
        f"\n\n{text}"
    )
