"""
Agent Loop - Core ReAct-style agent loop
"""

import asyncio
import uuid
import json
import re
from typing import Optional, Dict, Any, List

from .types import AgentState, ToolResult, Step, AgentConfig
from ..llm.gateway import LLMGateway
from ..tools.registry import ToolRegistry
from ..memory.short_term import ShortTermMemory
from ..logging import get_logger, TaskLogger

logger = get_logger("agent.loop")


class AgentLoop:
    """
    Core ReAct-style agent loop.

    Loop:
    1. THINK: LLM reasons about current state
    2. PLAN: LLM decides tool to call (if any)
    3. ACT: Execute tool via ToolRegistry
    4. OBSERVE: Process result, update context
    5. CHECK: Determine if task is complete
    """

    DEFAULT_SYSTEM_PROMPT = """You are {name}, an AI agent with access to tools.

You MUST follow the ReAct pattern:
- THINK: Reason about the current state and what to do next
- ACT: If action is needed, call a tool with {{"tool": "tool_name", "args": {{"arg1": "value1"}}}}
- OBSERVE: Process the result and continue

When you have completed the task, respond with:
FINAL_ANSWER: <your answer>

Available tools: {tools}
"""

    def __init__(
        self,
        config: AgentConfig,
        llm_gateway: LLMGateway,
        tool_registry: ToolRegistry,
        conversation: Optional[ShortTermMemory] = None,
        task_logger: Optional[TaskLogger] = None,
    ):
        self.config = config
        self.id = str(uuid.uuid4())[:8]
        self.state = AgentState.IDLE

        self.llm = llm_gateway
        self.tools = tool_registry
        self.conversation = conversation or ShortTermMemory()
        self.task_logger = task_logger or TaskLogger(self.id, config.name)

        self.iteration = 0
        self.steps: List[Step] = []

        # Build system prompt
        tool_names = list(self.tools.get_tool_names())
        self.system_prompt = config.system_prompt or self.DEFAULT_SYSTEM_PROMPT.format(
            name=config.name,
            tools=", ".join(tool_names) if tool_names else "none"
        )

        logger.info(f"Initialized agent {config.name} (id={self.id})")

    async def run(self, goal: str) -> Dict[str, Any]:
        """
        Main execution loop.

        Returns:
            Dictionary with success status, result, and execution metadata
        """
        self.task_logger.log_step("START", f"Goal: {goal}")
        self.conversation.add("user", goal)

        self.state = AgentState.THINKING

        try:
            while self.iteration < self.config.max_iterations:
                self.iteration += 1

                # THINK: Get LLM reasoning
                self.state = AgentState.THINKING
                thought = await self._think()

                step = Step(step_num=self.iteration, thought=thought)
                self.steps.append(step)

                # PLAN: Decide next action
                action = self._parse_action(thought)

                if action is None:
                    # No action needed, check if task is complete
                    if "FINAL_ANSWER:" in thought:
                        answer = thought.split("FINAL_ANSWER:")[1].strip()
                        self.state = AgentState.DONE
                        self.task_logger.log_step("DONE", f"Final answer: {answer[:200]}")
                        return {
                            "success": True,
                            "result": answer,
                            "iterations": self.iteration,
                            "steps": self.steps,
                        }
                    continue

                # ACT: Execute tool
                self.state = AgentState.ACTING
                step.action = action["tool"]
                step.action_args = action.get("args", {})

                tool_result = await self._act(step.action, step.action_args)
                step.tool_result = tool_result

                # OBSERVE: Process result
                self.state = AgentState.WAITING
                observation = self._format_observation(tool_result)
                step.observation = observation

                self.conversation.add("system", observation)
                self.conversation.add("assistant", f"I thought: {thought}\nI acted: {step.action}")

            # Max iterations reached
            self.state = AgentState.DONE
            return {
                "success": False,
                "error": "Max iterations reached",
                "iterations": self.iteration,
                "steps": self.steps,
            }

        except Exception as e:
            self.state = AgentState.ERROR
            logger.exception(f"Agent {self.config.name} failed")
            return {
                "success": False,
                "error": str(e),
                "steps": self.steps,
            }
        finally:
            self.task_logger.end()

    async def _think(self) -> str:
        """Get reasoning from LLM."""
        conversation_text = "\n".join([
            f"{m['role']}: {m['content']}"
            for m in self.conversation.to_llm_format()[-10:]
        ])

        response = await self.llm.generate(
            prompt=f"Previous conversation:\n{conversation_text}\n\nWhat should I do next? Think step by step about how to solve this task.",
            system_prompt=self.system_prompt,
            task_class="reason",
        )

        return response.content

    def _parse_action(self, thought: str) -> Optional[Dict]:
        """Parse tool call from LLM thought."""
        # Look for JSON tool call in format: {"tool": "name", "args": {...}}
        patterns = [
            r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"args"\s*:\s*(\{[^}]*\})\s*\}',
            r'\{\s*"tool"\s*:\s*"([^"]+)"\s*\}',
        ]

        for pattern in patterns:
            match = re.search(pattern, thought)
            if match:
                tool_name = match.group(1)
                if match.group(2):
                    try:
                        # Try to parse args as JSON
                        args_str = match.group(2)
                        # Fix single quotes if present
                        args_str = args_str.replace("'", '"')
                        args = json.loads(args_str)
                        return {"tool": tool_name, "args": args}
                    except json.JSONDecodeError:
                        return {"tool": tool_name, "args": {}}
                else:
                    return {"tool": tool_name, "args": {}}

        return None

    async def _act(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        """Execute a tool."""
        start_time = asyncio.get_event_loop().time()

        try:
            result = await self.tools.execute(tool_name, args)

            duration = (asyncio.get_event_loop().time() - start_time) * 1000

            self.task_logger.log_tool_call(tool_name, args, result)

            return ToolResult(
                tool=tool_name,
                args=args,
                success=True,
                result=result,
                duration_ms=duration,
            )
        except Exception as e:
            duration = (asyncio.get_event_loop().time() - start_time) * 1000
            error_msg = str(e)

            self.task_logger.log_tool_call(tool_name, args, error=error_msg)

            return ToolResult(
                tool=tool_name,
                args=args,
                success=False,
                error=error_msg,
                duration_ms=duration,
            )

    def _format_observation(self, result: ToolResult) -> str:
        """Format tool result as observation."""
        if result.success:
            result_str = str(result.result)
            if len(result_str) > 500:
                result_str = result_str[:500] + "..."
            return f"Tool '{result.tool}' returned: {result_str}"
        else:
            return f"Tool '{result.tool}' failed: {result.error}"