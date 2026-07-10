from math import sqrt
from typing import List

from sqlalchemy.orm import Session

from ..database import models
from ..llm.openai_service import OpenAIService
from ..llm.prompt import build_rag_prompt, build_summary_prompt


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.openai_service = OpenAIService()

    def retrieve_relevant_chunks(self, query: str, user_id: int, limit: int = 4) -> List[models.DocumentChunk]:
        query_embedding = self.openai_service.embed_text(query)
        chunks = (
            self.db.query(models.DocumentChunk)
            .join(models.Document)
            .filter(models.Document.owner_id == user_id)
            .order_by(models.DocumentChunk.id.asc())
            .all()
        )
        query_lower = query.lower()
        is_api_query = any(word in query_lower for word in [
            "api", "apis", "endpoint", "endpoints", "method", "methods", "route", "routes", "url", "urls"
        ])
        scored = []
        for chunk in chunks:
            text_str = chunk.text
            is_toc_chunk = False
            if text_str:
                noise_chars = text_str.count('.') + text_str.count('-') + text_str.count('_')
                noise_ratio = noise_chars / len(text_str) if len(text_str) > 0 else 0
                has_api_endpoints = any(verb in text_str for verb in ["GET ", "POST ", "PUT ", "DELETE "])
                
                is_toc_chunk = noise_ratio > 0.07
                
                # Skip Table of Contents or Index chunks only if it is NOT an API query
                if not is_api_query and noise_ratio > 0.12 and not has_api_endpoints:
                    continue

            emb = chunk.embedding
            if isinstance(emb, str):
                import json
                try:
                    emb = json.loads(emb)
                except Exception:
                    pass
            if isinstance(emb, list):
                score = self._cosine_similarity(query_embedding, emb)
                if is_api_query and text_str:
                    if is_toc_chunk:
                        # Give a major boost to Table of Contents chunks for API queries to prioritize structured index
                        score += 0.40
                    elif has_api_endpoints:
                        score += 0.15
                scored.append((score, chunk))
        # Stable sort: primary sort on similarity score descending, secondary sort on chunk id ascending
        scored.sort(key=lambda item: (item[0], -item[1].id), reverse=True)
        
        # Dynamically determine chunk limit based on query type (e.g. summaries need wider context)
        is_summary_query = is_api_query or any(word in query_lower for word in [
            "summary", "summarize", "overview", "explain", "brief", "whole", "all about",
            "list", "endpoints", "which", "what are all", "how many"
        ])
        actual_limit = max(limit, 80 if is_summary_query else 6)
        
        top_scored = scored[:actual_limit]
        
        # Re-sort the top matching chunks by document_id and chunk_index to present them in original reading order
        top_scored.sort(key=lambda item: (item[1].document_id, item[1].chunk_index))
        
        return [chunk for _, chunk in top_scored]

    async def answer_question(self, user_id: int, question: str) -> str:
        has_docs = self.db.query(models.Document).filter(models.Document.owner_id == user_id).first() is not None
        if has_docs:
            chunks = self.retrieve_relevant_chunks(question, user_id=user_id)
            context = "\n\n".join([chunk.text for chunk in chunks]) if chunks else ""
            prompt = build_rag_prompt(context, question)
        else:
            prompt = f"Question: {question}"

        system_prompt = (
            "You are a unified Agentic RAG Assistant. "
            "You have access to the user's uploaded document context and various tools (weather, datetime, calculator). "
            "1. If the document context contains the answer to the user's question, answer using that context. "
            "2. If the document context does not contain the answer, or if the user asks a general question "
            "(such as about the current weather, time, calculator expression, or general knowledge) "
            "that is not answered in the documents, you must use your general knowledge or invoke the appropriate tool "
            "to answer the question. Do NOT refuse to answer general queries just because they are not in the documents."
        )
        return await self.openai_service.async_chat_completion(system_prompt, prompt)

    async def stream_answer(self, user_id: int, question: str):
        has_docs = self.db.query(models.Document).filter(models.Document.owner_id == user_id).first() is not None
        if has_docs:
            chunks = self.retrieve_relevant_chunks(question, user_id=user_id)
            context = "\n\n".join([chunk.text for chunk in chunks]) if chunks else ""
            prompt = build_rag_prompt(context, question)
        else:
            prompt = f"Question: {question}"

        system_prompt = (
            "You are a unified Agentic RAG Assistant. "
            "You have access to the user's uploaded document context and various tools (weather, datetime, calculator). "
            "1. If the document context contains the answer to the user's question, answer using that context. "
            "2. If the document context does not contain the answer, or if the user asks a general question "
            "(such as about the current weather, time, calculator expression, or general knowledge) "
            "that is not answered in the documents, you must use your general knowledge or invoke the appropriate tool "
            "to answer the question. Do NOT refuse to answer general queries just because they are not in the documents."
        )
        async for chunk in self.openai_service.async_stream_chat_completion(system_prompt, prompt):
            yield chunk

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sqrt(sum(x * x for x in a))
        norm_b = sqrt(sum(y * y for y in b))
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

    def summarize_text(self, text: str) -> str:
        prompt = build_summary_prompt(text)
        return self.openai_service.chat_completion("Summarize the text below.", prompt)
