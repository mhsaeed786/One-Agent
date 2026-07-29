import abc
import json
import os
import requests
from typing import Any, Dict, List, Optional

class Provider(abc.ABC):
    """Base class for LLM providers."""

    @abc.abstractmethod
    def generate(self, messages: List[Dict[str, str]], tools: List[Dict] = None, **kwargs) -> Any:
        """Generate a response based on the input messages."""
        pass


class MockResponse:
    def __init__(self, content, tool_calls=None):
        class Message:
            def __init__(self, c, tc):
                self.content = c
                self.tool_calls = tc
        class Choice:
            def __init__(self, m):
                self.message = m
        self.choices = [Choice(Message(content, tool_calls))]


class OpenAICompatibleProvider(Provider):
    """
    A simple provider that supports any OpenAI-compatible API (e.g., OpenAI, vLLM, Ollama, Together, Groq).
    """
    def __init__(self, model: str = "gpt-4o-mini", api_key: str = None, base_url: str = "https://api.openai.com/v1"):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url.rstrip("/")

    def generate(self, messages: List[Dict[str, str]], tools: List[Dict] = None, **kwargs) -> Any:
        if self.model == "stub":
            # Mock testing path
            has_tool_response = any(m.get("role") == "tool" for m in messages)
            if tools and "use_tool" in str(messages) and not has_tool_response:
                return MockResponse(content=None, tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "web_scraper", "arguments": '{"url": "example.com"}'}}])
            return MockResponse(content=f"Mock response from simple OpenAI provider for messages: {len(messages)}")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            **kwargs
        }
        if tools:
            payload["tools"] = tools

        try:
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # Reconstruct an object similar to what the agent loop expects
            message_data = data["choices"][0]["message"]

            # Simple object mapping for compatibility with agent/core.py which expects objects
            class ObjectDict(dict):
                def __getattr__(self, name):
                    if name in self:
                        if isinstance(self[name], dict):
                            return ObjectDict(self[name])
                        elif isinstance(self[name], list):
                            return [ObjectDict(i) if isinstance(i, dict) else i for i in self[name]]
                        return self[name]
                    return super().__getattribute__(name)

            if "tool_calls" in message_data:
                # Ensure tool_calls are wrapped properly
                for tc in message_data["tool_calls"]:
                    if "function" in tc and isinstance(tc["function"], dict):
                        tc["function"] = ObjectDict(tc["function"])

            return MockResponse(
                content=message_data.get("content"),
                tool_calls=[ObjectDict(tc) for tc in message_data.get("tool_calls", [])] if "tool_calls" in message_data else None
            )

        except Exception as e:
            return MockResponse(content=f"Error communicating with OpenAI compatible API: {str(e)}")


class AnthropicCompatibleProvider(Provider):
    """
    A simple provider for Anthropic format.
    """
    def __init__(self, model: str = "claude-3-haiku-20240307", api_key: str = None, base_url: str = "https://api.anthropic.com/v1"):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.base_url = base_url.rstrip("/")

    def generate(self, messages: List[Dict[str, str]], tools: List[Dict] = None, **kwargs) -> Any:
        if self.model == "stub":
            return MockResponse(content=f"Mock response from Anthropic provider")

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        # Anthropic separates system message
        system_msg = ""
        anthropic_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                anthropic_messages.append({"role": m["role"], "content": m["content"]})

        payload = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", 1024),
            "messages": anthropic_messages
        }
        if system_msg:
            payload["system"] = system_msg

        # Tool handling requires format translation, keeping it simple for now
        # ... translation logic would go here if tools were provided ...

        try:
            response = requests.post(f"{self.base_url}/messages", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # Simple extraction
            content = ""
            if "content" in data and len(data["content"]) > 0:
                content = data["content"][0]["text"]

            return MockResponse(content=content)

        except Exception as e:
            return MockResponse(content=f"Error communicating with Anthropic API: {str(e)}")


class GeminiCompatibleProvider(Provider):
    """
    A simple provider for Gemini format.
    """
    def __init__(self, model: str = "gemini-1.5-flash", api_key: str = None):
        self.model = model
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")

    def generate(self, messages: List[Dict[str, str]], tools: List[Dict] = None, **kwargs) -> Any:
        if self.model == "stub":
            return MockResponse(content=f"Mock response from Gemini provider")

        # Simplified direct request to Gemini
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        # Convert messages to Gemini format
        gemini_contents = []
        for m in messages:
            role = "user" if m["role"] in ["user", "system"] else "model"
            gemini_contents.append({
                "role": role,
                "parts": [{"text": m["content"]}]
            })

        payload = {"contents": gemini_contents}

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            content = ""
            if "candidates" in data and len(data["candidates"]) > 0:
                content = data["candidates"][0]["content"]["parts"][0]["text"]

            return MockResponse(content=content)

        except Exception as e:
            return MockResponse(content=f"Error communicating with Gemini API: {str(e)}")
