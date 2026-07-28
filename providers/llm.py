import abc
from typing import Any, Dict, List
import litellm

class Provider(abc.ABC):
    """Base class for LLM providers."""

    @abc.abstractmethod
    def generate(self, messages: List[Dict[str, str]], tools: List[Dict] = None, **kwargs) -> Any:
        """Generate a response based on the input messages."""
        pass


class LiteLLMProvider(Provider):
    def __init__(self, model: str = "gpt-3.5-turbo", api_key: str = None):
        self.model = model
        if api_key:
            import os
            # LiteLLM mostly reads from env vars, but we can set it via kwargs if needed
            os.environ["OPENAI_API_KEY"] = api_key # Fallback simple approach
            os.environ["ANTHROPIC_API_KEY"] = api_key
            os.environ["GEMINI_API_KEY"] = api_key

    def generate(self, messages: List[Dict[str, str]], tools: List[Dict] = None, **kwargs) -> Any:
        try:
            # Using mock for testing if no key provided and model is stub to avoid api errors
            if self.model == "stub":
                class MockMessage:
                    def __init__(self, content, tool_calls=None):
                        self.content = content
                        self.tool_calls = tool_calls
                class MockChoice:
                    def __init__(self, message):
                        self.message = message
                class MockResponse:
                    def __init__(self, message):
                        self.choices = [MockChoice(message)]

                # Mock a tool call for testing
                has_tool_response = any(m.get("role") == "tool" for m in messages)
                if tools and "use_tool" in str(messages) and not has_tool_response:
                    return MockResponse(MockMessage(content=None, tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "web_scraper", "arguments": '{"url": "example.com"}'}}]))
                return MockResponse(MockMessage(content=f"Mock response from litellm for messages: {len(messages)}"))

            response = litellm.completion(
                model=self.model,
                messages=messages,
                tools=tools,
                **kwargs
            )
            return response
        except Exception as e:
            class ErrorMessage:
                def __init__(self, content):
                    self.content = content
            class ErrorChoice:
                def __init__(self, message):
                    self.message = message
            class ErrorResponse:
                def __init__(self, message):
                    self.choices = [ErrorChoice(message)]
            return ErrorResponse(ErrorMessage(f"Error communicating with LLM ({self.model}): {str(e)}"))

# Keep old classes as wrappers around litellm for backward compatibility
class OpenAIProvider(LiteLLMProvider):
    def __init__(self, api_key: str = None):
        super().__init__(model="gpt-4o-mini", api_key=api_key)

class AnthropicProvider(LiteLLMProvider):
    def __init__(self, api_key: str = None):
        super().__init__(model="claude-3-haiku-20240307", api_key=api_key)

class GeminiProvider(LiteLLMProvider):
    def __init__(self, api_key: str = None):
        super().__init__(model="gemini/gemini-1.5-flash", api_key=api_key)
