import os
from typing import Iterable
import logging
import json
import inspect

from openai import OpenAI, AsyncOpenAI
import numpy as np

from ..core.config import settings
from ..services.agent_tools import get_current_weather, get_current_datetime, calculator

logger = logging.getLogger(__name__)


AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current real-time weather details for a specific city location name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and country name, e.g. London, Paris, Tokyo, Mumbai"
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Get the current real-time date and time on the user's system.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Perform simple mathematical calculations and expressions safely.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The math expression to evaluate, e.g. '25 * 4 - (12 / 3)'"
                    }
                },
                "required": ["expression"]
            }
        }
    }
]

TOOL_FUNCTIONS = {
    "get_current_weather": get_current_weather,
    "get_current_datetime": get_current_datetime,
    "calculator": calculator
}

async def execute_tool(name: str, args: dict) -> str:
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return f"Tool '{name}' not found."
    try:
        if inspect.iscoroutinefunction(func):
            return await func(**args)
        else:
            return func(**args)
    except Exception as e:
        return f"Error executing tool '{name}': {str(e)}"


class OpenAIService:
    _local_model = None
    _local_model_loaded = False

    def __init__(self):
        api_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        
        # Check if the key is a Google Gemini API key (starts with 'AQ' or 'AIzaSy')
        is_gemini = api_key.startswith("AQ") or api_key.startswith("AIzaSy")
        
        if is_gemini:
            self.embedding_model = "gemini-embedding-001"
            self.chat_model = "gemini-2.5-flash"
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            self.async_client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
        else:
            self.embedding_model = settings.embedding_model
            self.chat_model = settings.openai_model
            self.client = OpenAI(api_key=api_key)
            self.async_client = AsyncOpenAI(api_key=api_key)
        # Initialize local embedding model if configured
        self.local_model = None
        if settings.use_local_embeddings:
            if not OpenAIService._local_model_loaded:
                try:
                    from sentence_transformers import SentenceTransformer
                    logger.info("Loading local embedding model: %s", settings.local_embedding_model)
                    OpenAIService._local_model = SentenceTransformer(settings.local_embedding_model)
                except Exception as exc:
                    logger.exception("Failed to load local embedding model: %s", exc)
                    OpenAIService._local_model = None
                finally:
                    OpenAIService._local_model_loaded = True
            self.local_model = OpenAIService._local_model

    def embed_text(self, text: str) -> list[float]:
        if self.local_model is not None and settings.use_local_embeddings:
            vec = self.local_model.encode([text])
            # SentenceTransformer returns numpy array; take first result
            return np.asarray(vec[0]).tolist()
        response = self.client.embeddings.create(model=self.embedding_model, input=text)
        return response.data[0].embedding

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        texts_list = list(texts)
        if not texts_list:
            return []

        # If local model is available and enabled, compute embeddings locally
        if self.local_model is not None and settings.use_local_embeddings:
            vecs = self.local_model.encode(texts_list)
            # vecs is an array shape (n, dim)
            return [np.asarray(v).tolist() for v in vecs]

        # Otherwise, call remote API in safe batches
        batch_size = 10
        embeddings: list[list[float]] = []
        for i in range(0, len(texts_list), batch_size):
            batch = texts_list[i : i + batch_size]
            response = self.client.embeddings.create(model=self.embedding_model, input=batch)
            embeddings.extend([item.embedding for item in response.data])
        return embeddings

    def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=3000,
        )
        return response.choices[0].message.content.strip()

    def stream_chat_completion(self, system_prompt: str, user_prompt: str):
        response = self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=3000,
            stream=True,
        )
        for event in response:
            if event.choices and event.choices[0].delta:
                yield event.choices[0].delta.content or ""

    async def async_chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        try:
            for _ in range(5):
                response = await self.async_client.chat.completions.create(
                    model=self.chat_model,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=3000,
                    tools=AVAILABLE_TOOLS,
                    tool_choice="auto",
                )
                
                message = response.choices[0].message
                if message.tool_calls:
                    messages.append(message)
                    for tool_call in message.tool_calls:
                        name = tool_call.function.name
                        args = json.loads(tool_call.function.arguments)
                        result = await execute_tool(name, args)
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": name,
                            "content": result
                        })
                    continue
                else:
                    return message.content.strip() if message.content else ""
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "rate limit" in err_str.lower() or "exhausted" in err_str.lower():
                logger.warning("[OpenAIService] API Quota or Rate Limit reached: %s", err_str)
                return "You have reached your API quota limit. Please try again after your quota resets or when your API limits refresh."
            elif "401" in err_str or "unauthenticated" in err_str.lower() or "authentication" in err_str.lower() or "unauthorized" in err_str.lower():
                logger.warning("[OpenAIService] API Authentication failed (401). Please check that your API key is correct and active: %s", err_str)
                return "Authentication failed. The API key in backend/.env is invalid, inactive, or copied incorrectly. Please check your configuration."
            logger.exception("Error in async_chat_completion: %s", e)
            return f"An error occurred: {err_str}"
                
        return "Error: Maximum tool call iterations reached."

    async def async_stream_chat_completion(self, system_prompt: str, user_prompt: str):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        try:
            for _ in range(5):
                response = await self.async_client.chat.completions.create(
                    model=self.chat_model,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=3000,
                    tools=AVAILABLE_TOOLS,
                    tool_choice="auto",
                    stream=True,
                )
                
                tool_calls = []
                text_content = []
                
                async for chunk in response:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if not delta:
                        continue
                    
                    # Check for tool calls
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index if tc.index is not None else 0
                            if len(tool_calls) <= idx:
                                while len(tool_calls) <= idx:
                                    tool_calls.append({
                                        "id": "",
                                        "name": "",
                                        "arguments": ""
                                    })
                            
                            if tc.id:
                                tool_calls[idx]["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    tool_calls[idx]["name"] = tc.function.name
                                if tc.function.arguments:
                                    tool_calls[idx]["arguments"] += tc.function.arguments
                    
                    # Check for content
                    if delta.content:
                        text_content.append(delta.content)
                        yield delta.content
                        
                if tool_calls:
                    assistant_message = {
                        "role": "assistant",
                        "content": "".join(text_content) if text_content else None,
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["name"],
                                    "arguments": tc["arguments"]
                                }
                            } for tc in tool_calls
                        ]
                    }
                    messages.append(assistant_message)
                    
                    for tc in tool_calls:
                        name = tc["name"]
                        args = json.loads(tc["arguments"])
                        result = await execute_tool(name, args)
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "name": name,
                            "content": result
                        })
                    continue
                else:
                    break
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "rate limit" in err_str.lower() or "exhausted" in err_str.lower():
                logger.warning("[OpenAIService] API Quota or Rate Limit reached: %s", err_str)
                yield "You have reached your API quota limit. Please try again after your quota resets or when your API limits refresh."
            elif "401" in err_str or "unauthenticated" in err_str.lower() or "authentication" in err_str.lower() or "unauthorized" in err_str.lower():
                logger.warning("[OpenAIService] API Authentication failed (401). Please check that your API key is correct and active: %s", err_str)
                yield "Authentication failed. The API key in backend/.env is invalid, inactive, or copied incorrectly. Please check your configuration."
            else:
                logger.exception("Error in async_stream_chat_completion: %s", e)
                yield f"An error occurred: {err_str}"

