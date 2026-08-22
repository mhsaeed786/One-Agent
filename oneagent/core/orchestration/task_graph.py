"""
Task Graph - Adapts src/orchestration/orchestrator.py
====================================================
Inspired by LangGraph Pregel execution model.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ..logging import get_logger, TaskLogger

logger = get_logger("orchestration.task_graph")


class ChannelType(Enum):
    """Types of state channels."""
    LAST_VALUE = "last_value"      # Keep only last value
    TOPIC = "topic"                # Accumulate all values
    BINARY_AGG = "binary_agg"      # Combine with operator
    EPHEMERAL = "ephemeral"        # Single-read then invalidate


class NodeStatus(Enum):
    """Status of a task node."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"


@dataclass
class TaskNode:
    """A node in the task graph."""
    id: str
    name: str
    func: Callable
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    retries: int = 3
    timeout: int = 300
    status: NodeStatus = NodeStatus.PENDING

    def __hash__(self):
        return hash(self.id)


@dataclass
class StateChannel:
    """A channel for state passing between nodes."""
    id: str
    channel_type: ChannelType = ChannelType.LAST_VALUE
    default: Any = None
    operator: Callable = field(default=lambda a, b: b)

    _value: Any = field(default=None, repr=False)

    def read(self) -> Any:
        """Read current value."""
        return self._value if self._value is not None else self.default

    def write(self, value: Any) -> None:
        """Write value based on channel type."""
        if self.channel_type == ChannelType.LAST_VALUE:
            self._value = value
        elif self.channel_type == ChannelType.TOPIC:
            if self._value is None:
                self._value = []
            self._value.append(value)
        elif self.channel_type == ChannelType.BINARY_AGG:
            self._value = self.operator(self._value, value)
        elif self.channel_type == ChannelType.EPHEMERAL:
            self._value = value

    def clear(self) -> None:
        """Clear the channel (for ephemeral)."""
        self._value = None


class TaskGraph:
    """
    Task graph for defining agent workflows.
    Inspired by LangGraph StateGraph.
    """

    def __init__(self, name: str = "task_graph"):
        self.name = name
        self.nodes: Dict[str, TaskNode] = {}
        self.channels: Dict[str, StateChannel] = {}
        self.edges: List[tuple] = []
        self.entry_point: Optional[str] = None
        self.conditional_edges: Dict[str, Callable] = {}

        logger.info(f"Created task graph: {name}")

    def add_node(self, func: Callable, name: str = None,
                 inputs: List[str] = None, outputs: List[str] = None) -> str:
        """Add a node to the graph."""
        node_id = name or func.__name__

        if node_id in self.nodes:
            raise ValueError(f"Node '{node_id}' already exists")

        node = TaskNode(
            id=node_id,
            name=node_id,
            func=func,
            inputs=inputs or [],
            outputs=outputs or []
        )
        self.nodes[node_id] = node

        logger.debug(f"Added node: {node_id}")
        return node_id

    def add_channel(self, channel_id: str,
                    channel_type: ChannelType = ChannelType.LAST_VALUE,
                    default: Any = None) -> StateChannel:
        """Add a state channel."""
        if channel_id in self.channels:
            raise ValueError(f"Channel '{channel_id}' already exists")

        channel = StateChannel(
            id=channel_id,
            channel_type=channel_type,
            default=default
        )
        self.channels[channel_id] = channel

        logger.debug(f"Added channel: {channel_id}")
        return channel

    def add_edge(self, from_node: str, to_node: str) -> None:
        """Add an edge between nodes."""
        if from_node not in self.nodes:
            raise ValueError(f"Unknown node: {from_node}")
        if to_node not in self.nodes:
            raise ValueError(f"Unknown node: {to_node}")

        self.edges.append((from_node, to_node))
        logger.debug(f"Added edge: {from_node} -> {to_node}")

    def set_entry_point(self, node_id: str) -> None:
        """Set the entry point node."""
        if node_id not in self.nodes:
            raise ValueError(f"Unknown node: {node_id}")
        self.entry_point = node_id

    def compile(self) -> 'CompiledGraph':
        """Compile the graph for execution."""
        return CompiledGraph(self)


class CompiledGraph:
    """Compiled task graph ready for execution."""

    def __init__(self, graph: TaskGraph):
        self.graph = graph
        self._checkpointer = None

    def set_checkpointer(self, checkpointer: Any) -> None:
        """Set checkpoint store for fault tolerance."""
        self._checkpointer = checkpointer

    async def execute(self, initial_state: Dict[str, Any],
                     thread_id: str = None,
                     stream: bool = True) -> Dict[str, Any]:
        """
        Execute the compiled graph.
        Inspired by LangGraph Pregel execution.
        """
        task_logger = TaskLogger(
            task_id=thread_id or str(uuid.uuid4())[:8],
            agent_name="graph_executor"
        )

        task_logger.log_step("START", f"Executing graph: {self.graph.name}")

        # Initialize channels with initial state
        for channel_id, value in initial_state.items():
            if channel_id in self.graph.channels:
                self.graph.channels[channel_id].write(value)
            else:
                # Auto-create channel if not exists
                self.graph.add_channel(channel_id)
                self.graph.channels[channel_id].write(value)

        # Build execution order using topological sort
        execution_order = self._topological_sort()

        results = {}
        node_states = {node_id: NodeStatus.PENDING for node_id in self.graph.nodes}

        for node_id in execution_order:
            node = self.graph.nodes[node_id]

            # Check if node is ready (all inputs available)
            if not self._is_node_ready(node):
                task_logger.log_step("SKIP", f"Node {node_id} waiting for inputs")
                node_states[node_id] = NodeStatus.WAITING
                continue

            task_logger.log_step("RUN", f"Executing node: {node_id}")
            node_states[node_id] = NodeStatus.RUNNING

            try:
                # Gather inputs from channels
                inputs = {
                    channel_id: self.graph.channels[channel_id].read()
                    for channel_id in node.inputs
                }

                # Execute node function
                if asyncio.iscoroutinefunction(node.func):
                    result = await asyncio.wait_for(
                        node.func(inputs),
                        timeout=node.timeout
                    )
                else:
                    result = node.func(inputs)

                # Write outputs to channels
                if isinstance(result, dict):
                    for channel_id, value in result.items():
                        if channel_id in self.graph.channels:
                            self.graph.channels[channel_id].write(value)

                results[node_id] = result
                node_states[node_id] = NodeStatus.COMPLETED
                task_logger.log_step("DONE", f"Node {node_id} completed")

            except Exception as e:
                logger.exception(f"Node {node_id} failed")
                node_states[node_id] = NodeStatus.FAILED
                results[node_id] = {"error": str(e)}

        task_logger.log_step("COMPLETE", f"Graph execution finished")
        task_logger.end()

        return {
            "results": results,
            "node_states": node_states,
            "final_state": {
                ch_id: ch.read()
                for ch_id, ch in self.graph.channels.items()
            }
        }

    def _topological_sort(self) -> List[str]:
        """Topological sort for execution order."""
        visited = set()
        order = []

        def visit(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)

            # Visit all predecessors first
            for from_node, to_node in self.graph.edges:
                if to_node == node_id:
                    visit(from_node)

            order.append(node_id)

        # Start from entry point or all nodes
        if self.graph.entry_point:
            visit(self.graph.entry_point)

        # Add any unvisited nodes
        for node_id in self.graph.nodes:
            if node_id not in visited:
                visit(node_id)

        return order

    def _is_node_ready(self, node: TaskNode) -> bool:
        """Check if all input channels have values."""
        for channel_id in node.inputs:
            if channel_id in self.graph.channels:
                value = self.graph.channels[channel_id].read()
                if value is None:
                    return False
        return True