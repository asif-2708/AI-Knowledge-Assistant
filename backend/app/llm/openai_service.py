import os
from typing import Iterable, Generator
import logging
import json
import inspect
import httpx

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


def _openai_to_anthropic_messages(openai_messages: list) -> tuple[str, list]:
    anthropic_messages = []
    system_prompt = ""
    for msg in openai_messages:
        role = msg["role"]
        if role == "system":
            system_prompt = msg["content"]
        elif role == "user":
            anthropic_messages.append({"role": "user", "content": msg["content"]})
        elif role == "assistant":
            content = []
            if msg.get("content"):
                content.append({"type": "text", "text": msg["content"]})
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    tc_id = tc["id"] if isinstance(tc, dict) else tc.id
                    tc_name = tc["function"]["name"] if isinstance(tc, dict) else tc.function.name
                    tc_args = tc["function"]["arguments"] if isinstance(tc, dict) else tc.function.arguments
                    if isinstance(tc_args, str):
                        try:
                            tc_args = json.loads(tc_args)
                        except Exception:
                            tc_args = {}
                    content.append({
                        "type": "tool_use",
                        "id": tc_id,
                        "name": tc_name,
                        "input": tc_args
                    })
            anthropic_messages.append({"role": "assistant", "content": content})
        elif role == "tool":
            tool_result = {
                "type": "tool_result",
                "tool_use_id": msg["tool_call_id"],
                "content": msg["content"]
            }
            if anthropic_messages and anthropic_messages[-1]["role"] == "user":
                last_msg = anthropic_messages[-1]
                if isinstance(last_msg["content"], list):
                    last_msg["content"].append(tool_result)
                else:
                    last_msg["content"] = [{"type": "text", "text": last_msg["content"]}, tool_result]
            else:
                anthropic_messages.append({"role": "user", "content": [tool_result]})
    return system_prompt, anthropic_messages


class OpenAIService:
    _local_model = None
    _local_model_loaded = False

    def __init__(self):
        api_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        
        # Detect LLM Provider
        if api_key.startswith("gsk_"):
            self.provider = "groq"
            self.chat_model = "llama-3.3-70b-versatile"
            self.embedding_model = ""
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1"
            )
            self.async_client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1"
            )
        elif api_key.startswith("sk-ant-"):
            self.provider = "anthropic"
            self.chat_model = "claude-3-5-sonnet-20241022"
            self.embedding_model = ""
            self.api_key = api_key
            self.httpx_client = httpx.Client(timeout=30.0)
            self.httpx_async_client = httpx.AsyncClient(timeout=30.0)
        elif api_key.startswith("AQ") or api_key.startswith("AIzaSy"):
            self.provider = "gemini"
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
            self.provider = "openai"
            self.embedding_model = settings.embedding_model
            self.chat_model = settings.openai_model
            self.client = OpenAI(api_key=api_key)
            self.async_client = AsyncOpenAI(api_key=api_key)

        # Initialize local embedding model if configured or if provider lacks embeddings API
        needs_local = settings.use_local_embeddings or self.provider in ["groq", "anthropic"]
        self.local_model = None
        if needs_local:
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
        if self.local_model is not None:
            vec = self.local_model.encode([text])
            return np.asarray(vec[0]).tolist()
        response = self.client.embeddings.create(model=self.embedding_model, input=text)
        return response.data[0].embedding

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        texts_list = list(texts)
        if not texts_list:
            return []

        if self.local_model is not None:
            vecs = self.local_model.encode(texts_list)
            return [np.asarray(v).tolist() for v in vecs]

        batch_size = 10
        embeddings: list[list[float]] = []
        for i in range(0, len(texts_list), batch_size):
            batch = texts_list[i : i + batch_size]
            response = self.client.embeddings.create(model=self.embedding_model, input=batch)
            embeddings.extend([item.embedding for item in response.data])
        return embeddings

    def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        if self.provider == "anthropic":
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            body = {
                "model": self.chat_model,
                "max_tokens": 3000,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.0
            }
            response = self.httpx_client.post("https://api.anthropic.com/v1/messages", json=body, headers=headers)
            response.raise_for_status()
            return response.json()["content"][0]["text"].strip()

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

    def stream_chat_completion(self, system_prompt: str, user_prompt: str) -> Generator[str, None, None]:
        if self.provider == "anthropic":
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            body = {
                "model": self.chat_model,
                "max_tokens": 3000,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.0,
                "stream": True
            }
            with self.httpx_client.stream("POST", "https://api.anthropic.com/v1/messages", json=body, headers=headers) as response:
                response.raise_for_status()
                current_event = None
                for line in response.iter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("event:"):
                        current_event = line[len("event:"):].strip()
                    elif line.startswith("data:"):
                        data_str = line[len("data:"):].strip()
                        if current_event == "content_block_delta":
                            try:
                                data = json.loads(data_str)
                                if data.get("delta", {}).get("type") == "text_delta":
                                    yield data["delta"]["text"]
                            except Exception:
                                pass
            return

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
        if self.provider == "anthropic":
            return await self._anthropic_async_chat(system_prompt, user_prompt)

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

    async def _anthropic_async_chat(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        anthropic_tools = [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "input_schema": t["function"]["parameters"]
            } for t in AVAILABLE_TOOLS
        ]
        
        try:
            for _ in range(5):
                sys_msg, ant_msgs = _openai_to_anthropic_messages(messages)
                body = {
                    "model": self.chat_model,
                    "max_tokens": 3000,
                    "system": sys_msg,
                    "messages": ant_msgs,
                    "temperature": 0.0,
                    "tools": anthropic_tools
                }
                
                response = await self.httpx_async_client.post(
                    "https://api.anthropic.com/v1/messages", 
                    json=body, 
                    headers=headers
                )
                response.raise_for_status()
                res_data = response.json()
                
                content_blocks = res_data.get("content", [])
                text_content = ""
                tool_calls = []
                
                for block in content_blocks:
                    if block["type"] == "text":
                        text_content += block["text"]
                    elif block["type"] == "tool_use":
                        tool_calls.append({
                            "id": block["id"],
                            "type": "function",
                            "function": {
                                "name": block["name"],
                                "arguments": json.dumps(block["input"])
                            }
                        })
                
                assistant_msg = {
                    "role": "assistant",
                    "content": text_content if text_content else None
                }
                if tool_calls:
                    assistant_msg["tool_calls"] = tool_calls
                
                messages.append(assistant_msg)
                
                if tool_calls:
                    for tc in tool_calls:
                        name = tc["function"]["name"]
                        args = json.loads(tc["function"]["arguments"])
                        result = await execute_tool(name, args)
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "name": name,
                            "content": result
                        })
                    continue
                else:
                    return text_content.strip()
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "rate limit" in err_str.lower() or "exhausted" in err_str.lower():
                return "You have reached your API quota limit. Please try again after your quota resets or when your API limits refresh."
            elif "401" in err_str or "unauthenticated" in err_str.lower() or "authentication" in err_str.lower() or "unauthorized" in err_str.lower():
                return "Authentication failed. The API key in backend/.env is invalid, inactive, or copied incorrectly. Please check your configuration."
            logger.exception("Error in anthropic_async_chat: %s", e)
            return f"An error occurred: {err_str}"
            
        return "Error: Maximum tool call iterations reached."

    async def async_stream_chat_completion(self, system_prompt: str, user_prompt: str):
        if self.provider == "anthropic":
            async for chunk in self._anthropic_async_stream_chat(system_prompt, user_prompt):
                yield chunk
            return

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

    async def _anthropic_async_stream_chat(self, system_prompt: str, user_prompt: str):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        anthropic_tools = [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "input_schema": t["function"]["parameters"]
            } for t in AVAILABLE_TOOLS
        ]
        
        try:
            for _ in range(5):
                sys_msg, ant_msgs = _openai_to_anthropic_messages(messages)
                body = {
                    "model": self.chat_model,
                    "max_tokens": 3000,
                    "system": sys_msg,
                    "messages": ant_msgs,
                    "temperature": 0.0,
                    "tools": anthropic_tools,
                    "stream": True
                }
                
                tool_calls = []
                text_content = []
                current_tool_index = None
                
                req = self.httpx_async_client.build_request(
                    "POST", "https://api.anthropic.com/v1/messages", 
                    json=body, headers=headers
                )
                
                response = await self.httpx_async_client.send(req, stream=True)
                response.raise_for_status()
                
                current_event = None
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("event:"):
                        current_event = line[len("event:"):].strip()
                    elif line.startswith("data:"):
                        data_str = line[len("data:"):].strip()
                        try:
                            data = json.loads(data_str)
                        except Exception:
                            continue
                        
                        if current_event == "content_block_start":
                            block = data.get("content_block", {})
                            if block.get("type") == "tool_use":
                                current_tool_index = data.get("index", 0)
                                while len(tool_calls) <= current_tool_index:
                                    tool_calls.append({
                                        "id": "",
                                        "name": "",
                                        "arguments": ""
                                    })
                                tool_calls[current_tool_index]["id"] = block.get("id", "")
                                tool_calls[current_tool_index]["name"] = block.get("name", "")
                                
                        elif current_event == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text_delta = delta.get("text", "")
                                text_content.append(text_delta)
                                yield text_delta
                            elif delta.get("type") == "input_json_delta":
                                json_delta = delta.get("partial_json", "")
                                idx = data.get("index", 0)
                                while len(tool_calls) <= idx:
                                    tool_calls.append({
                                        "id": "",
                                        "name": "",
                                        "arguments": ""
                                    })
                                tool_calls[idx]["arguments"] += json_delta
                
                await response.aclose()
                
                assistant_msg = {
                    "role": "assistant",
                    "content": "".join(text_content) if text_content else None
                }
                
                formatted_tool_calls = []
                for tc in tool_calls:
                    if tc["id"] and tc["name"]:
                        formatted_tool_calls.append({
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"]
                            }
                        })
                
                if formatted_tool_calls:
                    assistant_msg["tool_calls"] = formatted_tool_calls
                
                messages.append(assistant_msg)
                
                if formatted_tool_calls:
                    for tc in formatted_tool_calls:
                        name = tc["function"]["name"]
                        args = json.loads(tc["function"]["arguments"])
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
                yield "You have reached your API quota limit. Please try again after your quota resets or when your API limits refresh."
            elif "401" in err_str or "unauthenticated" in err_str.lower() or "authentication" in err_str.lower() or "unauthorized" in err_str.lower():
                yield "Authentication failed. The API key in backend/.env is invalid, inactive, or copied incorrectly. Please check your configuration."
            else:
                logger.exception("Error in anthropic_async_stream_chat: %s", e)
                yield f"An error occurred: {err_str}"


