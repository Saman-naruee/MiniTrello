import inspect
from colorama import Fore, Style

def custom_logger(message, color=Fore.BLUE):
    """Custom log function that also shows the calling line"""
    # Get the frame of the caller
    frame = inspect.currentframe().f_back
    # Get the line number and code context
    line_no = frame.f_lineno
    # Get the source code of the calling line
    filename = frame.f_code.co_filename
    # Print the calling line and the message
    print(f"{Fore.YELLOW}[{filename}:{line_no}]{Style.RESET_ALL}")
    print(color + str(message) + Style.RESET_ALL)
