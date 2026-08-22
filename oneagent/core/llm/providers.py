"""
AI Provider Base Classes and Implementations
============================================
Wraps src/providers/ with AIProvider, AIProviderFactory, and implementations
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncIterator
from dataclasses import dataclass


@dataclass
class AIResponse:
    """Standardized AI response."""
    content: str
    raw_response: Any
    model: str
    usage: Dict[str, int]
    finish_reason: str


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def generate(self, prompt: str,
                      system_prompt: str = None,
                      **kwargs) -> AIResponse:
        """Generate text from prompt."""
        pass

    @abstractmethod
    async def stream(self, prompt: str,
                    system_prompt: str = None,
                    **kwargs) -> AsyncIterator[str]:
        """Stream text generation."""
        pass

    def format_messages(self, prompt: str,
                       system_prompt: str = None,
                       history: List[Dict] = None) -> List[Dict]:
        """Format messages for the provider."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        return messages


class AIProviderFactory:
    """Factory for creating AI providers."""

    _providers = {}

    @classmethod
    def register(cls, name: str, provider_class: type):
        """Register a provider class."""
        cls._providers[name] = provider_class

    @classmethod
    def create(cls, provider_name: str, **kwargs) -> AIProvider:
        """Create a provider instance."""
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown provider: {provider_name}. Available: {list(cls._providers.keys())}")
        return cls._providers[provider_name](**kwargs)

    @classmethod
    def available_providers(cls) -> List[str]:
        """List available providers."""
        return list(cls._providers.keys())


# =============================================================================
# OPENAI PROVIDER
# =============================================================================

class OpenAIProvider(AIProvider):
    """OpenAI GPT provider."""

    def __init__(self, api_key: str = None, model: str = "gpt-4", **kwargs):
        self.api_key = api_key
        self.model = model
        self.client = None

    def _get_client(self):
        if self.client is None:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("OpenAI package not installed. Run: pip install openai")
        return self.client

    async def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> AIResponse:
        messages = self.format_messages(prompt, system_prompt)
        client = self._get_client()

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )

        return AIResponse(
            content=response.choices[0].message.content,
            raw_response=response,
            model=self.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            finish_reason=response.choices[0].finish_reason
        )

    async def stream(self, prompt: str, system_prompt: str = None, **kwargs) -> AsyncIterator[str]:
        messages = self.format_messages(prompt, system_prompt)
        client = self._get_client()

        stream = client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            **kwargs
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# =============================================================================
# ANTHROPIC PROVIDER
# =============================================================================

class AnthropicProvider(AIProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str = None, model: str = "claude-3-sonnet-20240229", **kwargs):
        self.api_key = api_key
        self.model = model
        self.client = None

    def _get_client(self):
        if self.client is None:
            try:
                from anthropic import AsyncAnthropic
                self.client = AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("Anthropic package not installed. Run: pip install anthropic")
        return self.client

    async def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> AIResponse:
        client = self._get_client()

        response = await client.messages.create(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 4096),
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}]
        )

        return AIResponse(
            content=response.content[0].text,
            raw_response=response,
            model=self.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            },
            finish_reason=response.stop_reason
        )

    async def stream(self, prompt: str, system_prompt: str = None, **kwargs) -> AsyncIterator[str]:
        client = self._get_client()

        async with client.messages.stream(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 4096),
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            async for text in stream.text_stream:
                yield text


# =============================================================================
# OLLAMA PROVIDER
# =============================================================================

class OllamaProvider(AIProvider):
    """Ollama local LLM provider."""

    def __init__(self, model: str = "llama2", host: str = None, **kwargs):
        self.model = model
        self.host = host or "http://localhost:11434"
        self.client = None

    def _get_client(self):
        if self.client is None:
            try:
                import ollama
                self.client = ollama
            except ImportError:
                raise ImportError("Ollama package not installed. Run: pip install ollama")
        return self.client

    async def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> AIResponse:
        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat(model=self.model, messages=messages)

        return AIResponse(
            content=response['message']['content'],
            raw_response=response,
            model=self.model,
            usage={},
            finish_reason="stop"
        )

    async def stream(self, prompt: str, system_prompt: str = None, **kwargs) -> AsyncIterator[str]:
        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = client.chat(model=self.model, messages=messages, stream=True)

        for chunk in stream:
            if chunk['message']['content']:
                yield chunk['message']['content']


# =============================================================================
# REGISTER PROVIDERS
# =============================================================================

# =============================================================================
# GEMINI PROVIDER
# =============================================================================

class GeminiProvider(AIProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: str = None, model: str = "gemini-2.0-flash", **kwargs):
        self.api_key = api_key
        self.model = model
        self.client = None

    def _get_client(self):
        if self.client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(self.model)
            except ImportError:
                raise ImportError(
                    "Google Generative AI package not installed. Run: pip install google-generativeai"
                )
        return self.client

    async def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> AIResponse:
        client = self._get_client()

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [system_prompt]})
            contents.append({"role": "model", "parts": ["Understood."]})
        contents.append({"role": "user", "parts": [prompt]})

        response = client.generate_content(
            contents,
            generation_config=kwargs.get("generation_config"),
        )

        usage_metadata = response.usage_metadata if hasattr(response, "usage_metadata") else None
        usage = {}
        if usage_metadata:
            usage = {
                "prompt_tokens": getattr(usage_metadata, "prompt_token_count", 0) or 0,
                "completion_tokens": getattr(usage_metadata, "candidates_token_count", 0) or 0,
                "total_tokens": getattr(usage_metadata, "total_token_count", 0) or 0,
            }

        return AIResponse(
            content=response.text,
            raw_response=response,
            model=self.model,
            usage=usage,
            finish_reason="stop",
        )

    async def stream(self, prompt: str, system_prompt: str = None, **kwargs) -> AsyncIterator[str]:
        client = self._get_client()

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [system_prompt]})
            contents.append({"role": "model", "parts": ["Understood."]})
        contents.append({"role": "user", "parts": [prompt]})

        response = client.generate_content(contents, stream=True)

        for chunk in response:
            if chunk.text:
                yield chunk.text


# =============================================================================
# REGISTER PROVIDERS
# =============================================================================

AIProviderFactory.register("openai", OpenAIProvider)
AIProviderFactory.register("anthropic", AnthropicProvider)
AIProviderFactory.register("ollama", OllamaProvider)
AIProviderFactory.register("gemini", GeminiProvider)