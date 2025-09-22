"""
Enhanced Object-Oriented Logger System
Following SOLID principles and best OOP practices
"""

import inspect
import os
from datetime import datetime
from abc import ABC, abstractmethod
from enum import Enum
from colorama import Fore, Style, Back, init
from typing import Dict, Optional, Any

# Initialize colorama for Windows compatibility
init(autoreset=True)

class LogLevel(Enum):
    """Enumeration for log levels with associated colors and priorities."""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    SUCCESS = 25

    @property
    def color(self) -> str:
        """Get the color associated with this log level."""
        color_map = {
            self.DEBUG: Fore.CYAN,
            self.INFO: Fore.GREEN,
            self.WARNING: Fore.YELLOW,
            self.ERROR: Fore.RED,
            self.CRITICAL: Fore.RED + Back.WHITE,
            self.SUCCESS: Fore.GREEN + Style.BRIGHT
        }
        return color_map.get(self, Fore.BLUE)

    @property
    def name(self) -> str:
        """Get the name associated with this log level."""
        name_map = {
            self.DEBUG: "DEBUG",
            self.INFO: "INFO",
            self.WARNING: "WARNING",
            self.ERROR: "ERROR",
            self.CRITICAL: "CRITICAL",
            self.SUCCESS: "SUCCESS"
        }
        return name_map.get(self, "UNKNOWN")

    @property
    def priority(self) -> int:
        """Get the priority of this log level."""
        return self.value

class LoggerConfig:
    """Configuration class for logger settings."""

    def __init__(self,
                 show_caller: bool = True,
                 show_timestamp: bool = True,
                 timestamp_format: str = '%Y-%m-%d %H:%M:%S',
                 color_output: bool = True,
                 level: LogLevel = LogLevel.INFO):
        self.show_caller = show_caller
        self.show_timestamp = show_timestamp
        self.timestamp_format = timestamp_format
        self.color_output = color_output
        self.level = level

    def should_log(self, level: LogLevel) -> bool:
        """Check if a message at the given level should be logged."""
        return level.priority >= self.level.priority

class LogFormatter:
    """Handles formatting of log messages."""

    def __init__(self, config: LoggerConfig):
        self.config = config

    def format_message(self,
                      message: Any,
                      level: LogLevel,
                      caller_info: Optional[str] = None,
                      timestamp: Optional[str] = None) -> str:
        """Format a log message with all components."""
        parts = []

        # Add caller information
        if self.config.show_caller and caller_info:
            caller_formatted = f"\n{Fore.YELLOW}[{caller_info}]{Style.RESET_ALL}\n"
            parts.append(caller_formatted)

        # Add timestamp
        if self.config.show_timestamp and timestamp:
            timestamp_formatted = f"{Fore.WHITE}{timestamp}{Style.RESET_ALL}"
            parts.append(timestamp_formatted)

        # Add level indicator
        if self.config.color_output:
            level_indicator = f"{level.color}[{level.name}]{Style.RESET_ALL}"
        else:
            level_indicator = f"[{level.name}]"
        parts.append(level_indicator)

        # Add message
        if self.config.color_output:
            message_colored = f"{level.color}{str(message)}{Style.RESET_ALL}"
        else:
            message_colored = str(message)
        parts.append(message_colored)

        # Filter out empty parts and join
        filtered_parts = [part for part in parts if part]
        return " | ".join(filtered_parts)

class LogHandler(ABC):
    """Abstract base class for log output handlers."""

    @abstractmethod
    def handle(self, formatted_message: str, level: LogLevel) -> None:
        """Handle the output of a formatted log message."""
        pass

class ConsoleLogHandler(LogHandler):
    """Console-based log handler."""

    def handle(self, formatted_message: str, level: LogLevel) -> None:
        """Output the log message to console."""
        print(formatted_message)

class CallerInfo:
    """Handles caller information extraction."""

    @staticmethod
    def get_detailed_caller_info() -> Optional[str]:
        """
        Get detailed caller information by traversing the stack.
        Handles nested calls from shortcut functions.
        """
        try:
            # Start from the current frame and look for the caller
            frame = inspect.currentframe()

            # Look at different depths based on the calling pattern
            for depth in range(1, 6):  # Try up to 5 levels up
                try:
                    candidate_frame = frame.f_back
                    for _ in range(depth):
                        if candidate_frame:
                            candidate_frame = candidate_frame.f_back

                    if candidate_frame and candidate_frame.f_code.co_filename:
                        filename = os.path.basename(candidate_frame.f_code.co_filename)

                        # Skip if we're still in our own logger files
                        if 'logger.py' not in filename and 'logging' not in filename:
                            line_no = candidate_frame.f_lineno
                            try:
                                # Try to get more context
                                func_name = candidate_frame.f_code.co_name
                                class_name = None

                                # Try to get class name if inside a method
                                if 'self' in candidate_frame.f_locals:
                                    for name, value in candidate_frame.f_locals.items():
                                        if name == 'self':
                                            class_name = value.__class__.__name__
                                            break

                                # Format detailed caller info
                                parts = [filename, str(line_no)]
                                if class_name and func_name != '<module>':
                                    parts.append(f"{class_name}.{func_name}")
                                elif func_name != '<module>':
                                    parts.append(func_name)

                                return ':'.join(parts)

                            except:
                                # Fallback to basic info
                                return f"{filename}:{line_no}"
                except:
                    continue
        except:
            pass

        return None

class CustomLogger:
    """
    Main logger class implementing OOP best practices:
    - Single Responsibility: Only handles logging
    - Open/Closed: Extensible through inheritance and composition
    - Liskov Substitution: Can be replaced with subclasses
    - Interface Segregation: Clear interfaces for handlers and formatters
    - Dependency Inversion: Depends on abstractions, not concrete classes
    """

    _instance = None

    def __init__(self, config: Optional[LoggerConfig] = None, handler: Optional[LogHandler] = None):
        self.config = config or LoggerConfig()
        self.handler = handler or ConsoleLogHandler()
        self.formatter = LogFormatter(self.config)
        self.caller_info = CallerInfo()

    def _get_timestamp(self) -> str:
        """Get formatted current timestamp."""
        return datetime.now().strftime(self.config.timestamp_format)

    def log(self, message: Any, level: LogLevel = LogLevel.INFO) -> None:
        """
        Core logging method with full OOP structure.
        """
        if not self.config.should_log(level):
            return

        # Get caller information
        caller_info = None
        if self.config.show_caller:
            caller_info = self.caller_info.get_detailed_caller_info()

        # Get timestamp
        timestamp = None
        if self.config.show_timestamp:
            timestamp = self._get_timestamp()

        # Format message
        formatted_message = self.formatter.format_message(
            message, level, caller_info, timestamp
        )

        # Handle output
        self.handler.handle(formatted_message, level)

    # Level-specific logging methods
    def debug(self, message: Any) -> None:
        """Log a debug message."""
        self.log(message, LogLevel.DEBUG)

    def info(self, message: Any) -> None:
        """Log an info message."""
        self.log(message, LogLevel.INFO)

    def warning(self, message: Any) -> None:
        """Log a warning message."""
        self.log(message, LogLevel.WARNING)

    def error(self, message: Any) -> None:
        """Log an error message."""
        self.log(message, LogLevel.ERROR)

    def critical(self, message: Any) -> None:
        """Log a critical message."""
        self.log(message, LogLevel.CRITICAL)

    def success(self, message: Any) -> None:
        """Log a success message."""
        self.log(message, LogLevel.SUCCESS)

    # Class methods for singleton access
    @classmethod
    def get_instance(cls) -> 'CustomLogger':
        """Get the singleton instance of the logger."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def configure(cls, config: LoggerConfig) -> None:
        """Configure the singleton logger instance."""
        cls._instance = cls(config)

# Singleton instance for backward compatibility
_logger = CustomLogger.get_instance()

# Backward-compatible module-level functions
def custom_logger(message: Any, level: str = "INFO", color: Optional[str] = None, show_caller: bool = True) -> None:
    """
    Backward-compatible function interface.
    Supports both string level names and LogLevel enum values.
    """
    # Handle legacy string levels
    if isinstance(level, str):
        level_map = {
            "DEBUG": LogLevel.DEBUG,
            "INFO": LogLevel.INFO,
            "WARNING": LogLevel.WARNING,
            "ERROR": LogLevel.ERROR,
            "CRITICAL": LogLevel.CRITICAL,
            "SUCCESS": LogLevel.SUCCESS
        }
        level_enum = level_map.get(level.upper(), LogLevel.INFO)
    else:
        level_enum = level

    _logger.log(message, level_enum)

def debug(message: Any) -> None:
    """Shortcut for debug level logging"""
    _logger.debug(message)

def info(message: Any) -> None:
    """Shortcut for info level logging"""
    _logger.info(message)

def warning(message: Any) -> None:
    """Shortcut for warning level logging"""
    _logger.warning(message)

def error(message: Any) -> None:
    """Shortcut for error level logging"""
    _logger.error(message)

def success(message: Any) -> None:
    """Shortcut for success level logging"""
    _logger.success(message)

def critical(message: Any) -> None:
    """Shortcut for critical level logging"""
    _logger.critical(message)
