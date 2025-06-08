"""
Utility for adding timestamps to console outputs.
Created by Vasia as requested by the development team.
"""

import datetime
import sys
from typing import Any

# Store original print function to avoid recursion
_original_print = print


def timestamped_print(*args, file=None, flush: bool = False, **kwargs) -> None:
    """
    Print message with timestamp prefix.
    
    Args:
        *args: Arguments to print (like built-in print)
        file: File to write to (default: sys.stdout)
        flush: Whether to forcibly flush the stream
        **kwargs: Additional arguments passed to print()
    """
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _original_print(f'[{timestamp}]', *args, file=file, flush=flush, **kwargs)


def setup_global_timestamped_print() -> None:
    """
    Replace built-in print with timestamped version globally.
    Use with caution - affects all print statements in the application.
    """
    import builtins
    builtins.print = timestamped_print


def patch_logging_with_timestamps():
    """
    Patch Python logging to include timestamps in a consistent format.
    """
    import logging
    
    # Create custom formatter
    formatter = logging.Formatter(
        fmt='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Apply to root logger
    for handler in logging.root.handlers:
        handler.setFormatter(formatter)


# Example usage
if __name__ == "__main__":
    print("Testing timestamped print functionality:")
    timestamped_print("This is a test message")
    timestamped_print("Another test with multiple", "arguments")
    
    # Test the global replacement
    print("\nTesting global replacement:")
    setup_global_timestamped_print()
    print("Now all prints have timestamps!")
    print("This works for any print statement") 