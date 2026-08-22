import json
import logging
import time
from typing import List, Dict, Any

from providers.llm import Provider, ProviderError

logger = logging.getLogger(__name__)


def _wrap_tool_result(tool_output: Any) -> str:
    """Wrap a tool result as a structured {status, data} JSON envelope."""
    if isinstance(tool_output, dict) and "status" in tool_output:
        # Already structured
        return json.dumps(tool_output)
    if isinstance(tool_output, dict) and isinstance(tool_output.get("error"), str):
        return json.dumps({"status": "error", "data": tool_output})
    return json.dumps({"status": "ok", "data": tool_output})


class SuperAgent:
    def __init__(self, provider: Provider, memory_system: Any = None):
        self.provider = provider
        self.memory_system = memory_system
        self.conversation_history: List[Dict[str, Any]] = []
        self.tools = {}
        self.tool_schemas = []

    def add_tool(self, tool):
        """Register a tool with the agent."""
        self.tools[tool.name] = tool
        # Generate basic schema for tool calling
        schema = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": getattr(tool, "description", ""),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "arg": {
                            "type": "string",
                            "description": "Argument for the tool"
                        }
                    },
                    "required": ["arg"]
                }
            }
        }

        # Customize schema slightly based on tool
        if tool.name == "web_scraper":
            schema["function"]["parameters"]["properties"] = {"url": {"type": "string"}}
            schema["function"]["parameters"]["required"] = ["url"]
        elif tool.name == "computer_controller":
            schema["function"]["parameters"]["properties"] = {"action": {"type": "string"}}
            schema["function"]["parameters"]["required"] = ["action"]
        elif tool.name == "graph_api_integration":
            schema["function"]["parameters"]["properties"] = {"query": {"type": "string"}}
            schema["function"]["parameters"]["required"] = ["query"]

        self.tool_schemas.append(schema)

    def _execute_tool(self, function_name: str, function_args: Dict[str, Any]) -> str:
        """Execute a single tool call and return a structured JSON result envelope."""
        start = time.monotonic()
        args_summary = ", ".join(f"{k}={str(v)[:60]}" for k, v in list(function_args.items())[:3])

        try:
            if function_name not in self.tools:
                result = {"status": "error", "data": f"Tool {function_name} not found"}
            else:
                tool = self.tools[function_name]
                # Extract the first argument value generically since we just mapped single args above
                arg_val = list(function_args.values())[0] if function_args else ""
                output = tool.execute(arg_val)
                result = json.loads(_wrap_tool_result(output))
        except Exception as e:
            logger.exception("Tool %s raised", function_name)
            result = {"status": "error", "data": f"{type(e).__name__}: {e}"}

        duration_ms = (time.monotonic() - start) * 1000
        logger.debug(
            "tool=%s args=[%s] status=%s duration_ms=%.1f",
            function_name, args_summary, result.get("status"), duration_ms,
        )
        return json.dumps(result)

    def process_input(self, user_input: str) -> str:
        """Core loop to process input, consult memory, use tools, and generate response."""

        # 1. Update memory / context
        if self.memory_system:
            self.memory_system.add_interaction("user", user_input)
            context = self.memory_system.get_context()
        else:
            context = ""

        # Add to local history
        self.conversation_history.append({"role": "user", "content": user_input})

        system_msg = "You are a Super AI Agent. You can use tools to help the user."
        if context:
            system_msg += f"\n\nRelevant past context:\n{context}"

        messages = [{"role": "system", "content": system_msg}] + self.conversation_history.copy()

        # 2. Generate response with tool support; provider failures surface as an error envelope
        start = time.monotonic()
        try:
            response = self.provider.generate(messages, tools=self.tool_schemas if self.tool_schemas else None)
        except ProviderError as e:
            logger.debug("provider.generate failed in %.1fms: %s", (time.monotonic() - start) * 1000, e)
            return json.dumps({"status": "error", "data": f"LLM provider failed: {e}"})
        response_message = response.choices[0].message

        # Handle tool calls with an iteration cap to prevent runaway loops
        MAX_TOOL_ITERATIONS = 10
        iterations = 0
        while hasattr(response_message, "tool_calls") and response_message.tool_calls:
            iter_start = time.monotonic()
            iterations += 1
            if iterations > MAX_TOOL_ITERATIONS:
                print(f"Tool-loop iteration cap ({MAX_TOOL_ITERATIONS}) reached; forcing final answer.", flush=True)
                break

            logger.debug(
                "iteration=%d tool_calls=%d", iterations, len(response_message.tool_calls),
            )

            # Add assistant message with tool calls to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_message.content,
                "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} if not isinstance(tc, dict) else tc for tc in response_message.tool_calls]
            })

            # Execute tools
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name if not isinstance(tool_call, dict) else tool_call["function"]["name"]
                function_args_str = tool_call.function.arguments if not isinstance(tool_call, dict) else tool_call["function"]["arguments"]

                if isinstance(function_args_str, dict):
                    function_args = function_args_str
                else:
                    try:
                        function_args = json.loads(function_args_str)
                    except (json.JSONDecodeError, TypeError):
                        function_args = {}

                tool_output = self._execute_tool(function_name, function_args)

                # Add tool result to history
                tool_call_id = tool_call.id if not isinstance(tool_call, dict) else tool_call["id"]
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": function_name,
                    "content": tool_output
                })

            # Send results back to LLM
            messages = [{"role": "system", "content": system_msg}] + self.conversation_history.copy()
            response = self.provider.generate(messages, tools=self.tool_schemas if self.tool_schemas else None)
            response_message = response.choices[0].message
            logger.debug(
                "iteration=%d completed in %.1fms", iterations, (time.monotonic() - iter_start) * 1000,
            )

        final_content = response_message.content or "Done executing tools."

        # 3. Update memory with response
        if self.memory_system:
            self.memory_system.add_interaction("agent", final_content)

        self.conversation_history.append({"role": "assistant", "content": final_content})

        return final_content
