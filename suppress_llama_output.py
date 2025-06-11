#!/usr/bin/env python3
"""
Utility script to suppress llama.cpp debug output.
Place this in the root directory and import it at startup.
"""

import os
import sys
import io

class NullIO(io.StringIO):
    """A stream that silently discards all writes."""
    def write(self, txt):
        pass

# Redirect stderr during llama.cpp model loading 
def suppress_llama_output():
    """
    Suppress noisy llama.cpp model loading messages by redirecting stderr.
    Must be called before importing any llama.cpp-related modules.
    """
    # Set environment variable for llama.cpp to be quiet
    os.environ["LLAMA_CPP_VERBOSE"] = "0"
    
    # Save original stderr
    original_stderr = sys.stderr
    
    # Replace with null output
    sys.stderr = NullIO()
    
    # After imports, restore it
    # You should call restore_output() after model loading is complete
    return original_stderr
    
def restore_output(original_stderr):
    """Restore original stderr after model loading."""
    sys.stderr = original_stderr

# Example usage:
# import suppress_llama_output
# stderr = suppress_llama_output.suppress_llama_output()
# import your_llama_using_module
# suppress_llama_output.restore_output(stderr)