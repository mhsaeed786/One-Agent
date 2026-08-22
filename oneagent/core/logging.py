"""
Logging Module - Unified Logging Infrastructure
================================================
Inspired by: OpenHands, SuperAGI, LangGraph

Features:
- Multi-level logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Structured JSON logging
- Colorized console output
- File rotation
- Task context tracking
- Line-by-line execution tracing
"""

import logging
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from enum import Enum
from dataclasses import dataclass, field
import threading
import uuid

# ============================================================================
# LOG LEVELS & ENUMS
# ============================================================================

class LogLevel(Enum):
    """Log level enumeration matching Python logging levels."""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

# ============================================================================
# LOG CONFIGURATION
# ============================================================================

@dataclass
class LogConfig:
    """Configuration for the logging system."""
    level: LogLevel = LogLevel.INFO
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    enable_colors: bool = True
    enable_json: bool = False
    enable_console: bool = True
    enable_file: bool = True
    task_context: Optional[str] = None

# ============================================================================
# CONTEXT TRACKING
# ============================================================================

class TaskContext:
    """
    Tracks context for a specific task/agent execution.
    Inspired by OpenHands event stream.
    """

    _local = threading.local()

    def __init__(self, task_id: Optional[str] = None, agent_name: str = "root"):
        self.task_id = task_id or str(uuid.uuid4())[:8]
        self.agent_name = agent_name
        self.started_at = datetime.now()
        self.metadata: Dict[str, Any] = {}

    @classmethod
    def get_current(cls) -> Optional['TaskContext']:
        """Get the current task context for this thread."""
        return getattr(cls._local, 'context', None)

    @classmethod
    def set_current(cls, context: 'TaskContext') -> None:
        """Set the current task context for this thread."""
        cls._local.context = context

    @classmethod
    def clear_current(cls) -> None:
        """Clear the current task context."""
        cls._local.context = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "started_at": self.started_at.isoformat(),
            "metadata": self.metadata,
        }

# ============================================================================
# JSON FORMATTER
# ============================================================================

class JSONFormatter(logging.Formatter):
    """Formats log records as JSON for machine parsing."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add task context if available
        ctx = TaskContext.get_current()
        if ctx:
            log_data["task_context"] = ctx.to_dict()

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add extra fields
        if hasattr(record, 'extra_data'):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data)

# ============================================================================
# COLORED CONSOLE FORMATTER
# ============================================================================

class ColoredFormatter(logging.Formatter):
    """Formats log records with ANSI colors for terminal output."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m',
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        # Get task context info
        ctx = TaskContext.get_current()
        task_info = f"[{ctx.task_id}] " if ctx else ""

        # Format the message
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]
        level = record.levelname.ljust(8)
        location = f"{record.module}:{record.lineno}"

        formatted = (
            f"{color}[{timestamp}]{reset} "
            f"{task_info}{color}{level}{reset} "
            f"{record.getMessage()}"
        )

        # Add location for debug
        if record.levelno <= logging.DEBUG:
            formatted += f" {color}({location}){reset}"

        # Add exception info
        if record.exc_info:
            formatted += f"\n{color}{''.join(traceback.format_exception(*record.exc_info))}{reset}"

        return formatted

# ============================================================================
# SUPER APP LOGGER
# ============================================================================

class SuperAppLogger:
    """
    Main logger class for the AI Super App.
    Provides unified logging with context tracking and multiple outputs.

    Inspired by: OpenHands event stream, LangGraph callbacks, SuperAGI logging
    """

    _instances: Dict[str, 'SuperAppLogger'] = {}
    _lock = threading.Lock()

    def __init__(self, name: str, config: Optional[LogConfig] = None):
        self.name = name
        self.config = config or LogConfig()
        self._logger = logging.getLogger(name)
        self._setup_logger()

    @classmethod
    def get_logger(cls, name: str, config: Optional[LogConfig] = None) -> 'SuperAppLogger':
        """Get or create a logger instance (singleton per name)."""
        with cls._lock:
            if name not in cls._instances:
                cls._instances[name] = cls(name, config)
            return cls._instances[name]

    def _setup_logger(self) -> None:
        """Setup the logger with handlers and formatters."""
        # Clear existing handlers
        self._logger.handlers.clear()
        self._logger.setLevel(self.config.level.value)

        # Console handler
        if self.config.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.config.level.value)
            if self.config.enable_json:
                console_handler.setFormatter(JSONFormatter())
            else:
                console_handler.setFormatter(ColoredFormatter())
            self._logger.addHandler(console_handler)

        # File handler
        if self.config.enable_file:
            self.config.log_dir.mkdir(parents=True, exist_ok=True)
            log_file = self.config.log_dir / f"{self.name}.log"

            # Use rotating file handler for log rotation
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count,
            )
            file_handler.setLevel(self.config.level.value)
            if self.config.enable_json:
                file_handler.setFormatter(JSONFormatter())
            else:
                file_handler.setFormatter(
                    logging.Formatter(
                        "[%(asctime)s] %(levelname)s %(name)s:%(module)s:%(funcName)s:%(lineno)d - %(message)s"
                    )
                )
            self._logger.addHandler(file_handler)

    def _log(self, level: int, message: str, *args, **kwargs) -> None:
        """Internal log method that adds context."""
        extra_data = kwargs.pop('extra', {})

        # Create log record with extra data
        record = self._logger.makeRecord(
            self._logger.name,
            level,
            "(unknown)",
            0,
            message % args if args else message,
            None,
            None,
        )
        record.extra_data = extra_data

        self._logger.handle(record)

    def debug(self, message: str, *args, **kwargs) -> None:
        """Log debug message with line tracing."""
        self._log(logging.DEBUG, message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """Log info message."""
        self._log(logging.INFO, message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs) -> None:
        """Log exception with traceback."""
        self._log(logging.ERROR, message, *args, exc_info=True, **kwargs)

    # Context manager support
    def bind_context(self, **kwargs) -> 'LogContext':
        """Create a context manager for binding extra data."""
        return LogContext(self, kwargs)

    def task_context(self, task_id: str, agent_name: str = "agent") -> 'TaskContext':
        """Set up a task context for this logger."""
        ctx = TaskContext(task_id, agent_name)
        TaskContext.set_current(ctx)
        return ctx

# ============================================================================
# LOG CONTEXT MANAGER
# ============================================================================

class LogContext:
    """Context manager for binding extra data to log messages."""

    def __init__(self, logger: SuperAppLogger, extra: Dict[str, Any]):
        self.logger = logger
        self.extra = extra
        self._old_factory = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

# ============================================================================
# DECORATOR FOR FUNCTION TRACING
# ============================================================================

def trace(logger: Optional[SuperAppLogger] = None):
    """
    Decorator to trace function execution with entry/exit logs.

    Usage:
        @trace()
        def my_function(arg1, arg2):
            # ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            _logger = logger or SuperAppLogger.get_logger(func.__module__)

            # Log function entry
            args_repr = [repr(a) for a in args]
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)

            _logger.debug(f"ENTER: {func.__name__}({signature})")

            try:
                result = func(*args, **kwargs)
                _logger.debug(f"EXIT: {func.__name__} -> {type(result).__name__}")
                return result
            except Exception as e:
                _logger.exception(f"EXCEPTION in {func.__name__}: {e}")
                raise

        return wrapper
    return decorator

# ============================================================================
# TASK LOGGING HELPER
# ============================================================================

class TaskLogger:
    """
    Specialized logger for task/agent execution.
    Provides structured logging with task ID tracking.

    Inspired by OpenHands event stream.
    """

    def __init__(self, task_id: str, agent_name: str,
                 log_file: Optional[Path] = None,
                 config: Optional[LogConfig] = None):
        self.task_id = task_id
        self.agent_name = agent_name
        self.config = config or LogConfig()
        self.logger = SuperAppLogger.get_logger(f"task.{task_id}", self.config)

        # Set up task context
        self._ctx = TaskContext(task_id, agent_name)
        TaskContext.set_current(self._ctx)

    def log_step(self, step_name: str, action: str,
                 details: Optional[Dict[str, Any]] = None) -> None:
        """Log a task step with structured data."""
        self.logger.info(f"[STEP: {step_name}] {action}", extra=details or {})

    def log_tool_call(self, tool_name: str, args: Dict[str, Any],
                      result: Any = None, error: Optional[str] = None) -> None:
        """Log a tool call with arguments and result."""
        log_data = {
            "tool": tool_name,
            "args": args,
            "result_type": type(result).__name__ if result else None,
            "error": error,
        }
        if result and not error:
            # Truncate long results
            result_str = str(result)
            log_data["result_preview"] = result_str[:500] + "..." if len(result_str) > 500 else result_str

        self.logger.debug(f"TOOL_CALL: {tool_name}", extra=log_data)

    def log_thought(self, thought: str, reasoning: str) -> None:
        """Log agent thought process."""
        self.logger.debug(f"THOUGHT: {thought}", extra={
            "thought": thought,
            "reasoning": reasoning,
        })

    def log_observation(self, observation: str) -> None:
        """Log environment observation."""
        self.logger.debug(f"OBSERVATION: {observation[:500]}...")

    def end(self) -> None:
        """End the task context."""
        TaskContext.clear_current()

# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_logger(name: str, **kwargs) -> SuperAppLogger:
    """Get a logger instance."""
    return SuperAppLogger.get_logger(name, LogConfig(**kwargs))

def set_log_level(level: str) -> None:
    """Set global log level."""
    config = LogConfig(level=LogLevel[level.upper()])
    for logger in SuperAppLogger._instances.values():
        logger._logger.setLevel(config.level.value)

# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "LogLevel",
    "LogConfig",
    "TaskContext",
    "SuperAppLogger",
    "TaskLogger",
    "LogContext",
    "trace",
    "get_logger",
    "set_log_level",
    "JSONFormatter",
    "ColoredFormatter",
]