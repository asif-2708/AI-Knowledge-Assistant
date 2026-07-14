from langchain_core.prompts import PromptTemplate


rag_prompt_template = PromptTemplate.from_template(
    "You are a helpful assistant. Use the provided context from the user's documents to answer the question. "
    "If the document content does not contain an answer, say you do not know."
    "\n\nContext:\n{context}\n\nQuestion: {question}"
)

summary_prompt_template = PromptTemplate.from_template(
    "Summarize the following text in concise bullet points while preserving meaning and technical details."
    "\n\n{text}"
)


def build_rag_prompt(context: str, question: str) -> str:
    return rag_prompt_template.format(context=context, question=question)


def build_summary_prompt(text: str) -> str:
    return summary_prompt_template.format(text=text)

