from typing import List, Dict, Any
from providers.llm import Provider
import json

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
        messages = [{"role": "system", "content": system_msg}] + self.conversation_history.copy()

        # 3. Generate response with tool support
        response = self.provider.generate(messages, tools=self.tool_schemas if self.tool_schemas else None)
        response_message = response.choices[0].message

        # Handle tool calls
        while hasattr(response_message, "tool_calls") and response_message.tool_calls:
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

                try:
                    function_args = json.loads(function_args_str)
                except json.JSONDecodeError:
                    function_args = {}

                tool_output = f"Tool {function_name} not found"
                if function_name in self.tools:
                    tool = self.tools[function_name]
                    # Extract the first argument value generically since we just mapped single args above
                    arg_val = list(function_args.values())[0] if function_args else ""
                    tool_output = tool.execute(arg_val)

                # Add tool result to history
                tool_call_id = tool_call.id if not isinstance(tool_call, dict) else tool_call["id"]
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": function_name,
                    "content": str(tool_output)
                })

            # Send results back to LLM
            messages = [{"role": "system", "content": system_msg}] + self.conversation_history.copy()
            response = self.provider.generate(messages, tools=self.tool_schemas if self.tool_schemas else None)
            response_message = response.choices[0].message


        final_content = response_message.content or "Done executing tools."

        # 4. Update memory with response
        if self.memory_system:
            self.memory_system.add_interaction("agent", final_content)

        self.conversation_history.append({"role": "assistant", "content": final_content})

        return final_content
