import inspect
import os
from datetime import datetime
from colorama import Fore, Style, Back, init

# Initialize colorama for Windows compatibility
init(autoreset=True)

def _get_detailed_caller_info(level):
    """
    Get detailed caller information by traversing the stack.
    Handles nested calls from shortcut functions.
    """
    try:
        # Start from the current frame and look for the caller
        # The stack depth depends on whether called directly or through shortcuts
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

                            return f"\n{Fore.YELLOW}[{':'.join(parts)}]{Style.RESET_ALL}\n"

                        except:
                            # Fallback to basic info
                            return f"{Fore.YELLOW}[{filename}:{line_no}]{Style.RESET_ALL}"
            except:
                continue
    except:
        pass

    return ""

def custom_logger(message, level="INFO", color=None, show_caller=True):
    """
    Enhanced custom logger with multiple features:
    - Timestamps
    - Different log levels
    - Color coding based on log level
    - Detailed file, line number, class and method tracking
    - Better formatting
    """

    # Define log level colors
    level_colors = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED + Back.WHITE,
        "SUCCESS": Fore.GREEN + Style.BRIGHT
    }

    # Use provided color or get color based on level
    if color is None:
        color = level_colors.get(level.upper(), Fore.BLUE)

    # Get timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Get caller information if requested
    caller_info = ""
    if show_caller:
        caller_info = _get_detailed_caller_info(level)

    # Format the log entry
    level_indicator = f"[{level.upper()}]"
    if level.upper() in level_colors:
        level_indicator = f"{color}[{level.upper()}]{Style.RESET_ALL}"

    # Combine all parts
    log_parts = [
        caller_info,
        f"{Fore.WHITE}{timestamp}{Style.RESET_ALL}",
        level_indicator,
        color + str(message) + Style.RESET_ALL
    ]

    # Filter out empty parts and join
    log_parts = [part for part in log_parts if part]
    print(" | ".join(log_parts))

def debug(message):
    """Shortcut for debug level logging"""
    custom_logger(message, "DEBUG")

def info(message):
    """Shortcut for info level logging"""
    custom_logger(message, "INFO")

def warning(message):
    """Shortcut for warning level logging"""
    custom_logger(message, "WARNING")

def error(message):
    """Shortcut for error level logging"""
    custom_logger(message, "ERROR")

def success(message):
    """Shortcut for success level logging"""
    custom_logger(message, "SUCCESS")

def critical(message):
    """Shortcut for critical level logging"""
    custom_logger(message, "CRITICAL")
