#!/usr/bin/env python3
"""
Utility to suppress llama.cpp output.
Import this module and use it as a context manager.
"""

import os
import sys
import contextlib

@contextlib.contextmanager
def suppress_llama_output():
    """
    Context manager to suppress llama.cpp output.
    Usage: 
        with suppress_llama_output():
            # code that loads llama.cpp models
    """
    # Set environment variable to quiet llama.cpp
    old_verbose = os.environ.get("LLAMA_DEBUG", "")
    os.environ["LLAMA_DEBUG"] = "0"
    
    # Save original stdout/stderr
    old_stdout, old_stderr = sys.stdout, sys.stderr
    
    # Create null device
    try:
        with open(os.devnull, 'w') as devnull:
            # Redirect stdout and stderr to /dev/null
            sys.stdout = devnull
            sys.stderr = devnull
            
            # Execute the wrapped code
            try:
                yield
            finally:
                # Restore original stdout/stderr
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                
                # Restore environment variable
                if old_verbose:
                    os.environ["LLAMA_DEBUG"] = old_verbose
                else:
                    os.environ.pop("LLAMA_DEBUG", None)
    except Exception as e:
        # In case of error opening /dev/null
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        print(f"Error in suppress_llama_output: {e}")
        yield

# If imported directly in prometheus.py, add this line:
# from suppress_llama import suppress_llama_output