#!/usr/bin/env python3
"""
Patch file to modify debug output in Prometheus.
Run this script to make the changes.
"""

import re
import sys
import os

def patch_base_entity():
    """
    Patch the BaseEntity class to remove noisy debug output.
    """
    filepath = "core/base_entity.py"
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found")
        return False
        
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Remove print statements with [BaseEntity]
    content = re.sub(r'print\(f"\[BaseEntity\].*?\)', '# Debug output removed', content)
    
    # Clean up _display_debug_summary to hide output
    debug_pattern = r'def _display_debug_summary.*?route_str = f"{route_used\.upper\(\)}".*?# Print minimal summary.*?print\(.*?\)'
    debug_repl = '''def _display_debug_summary(self, user_input: str, result: dict[str, Any], total_time: float) -> None:
        """Display comprehensive debug information about the thinking process."""
        execution_details = result.get("execution_details", {})
        route_used = execution_details.get("route_used", "unknown")
        approach = execution_details.get("approach", "unknown")
        fast_track = execution_details.get("fast_track", False)
        
        # Get provider info if available
        consultation_metadata = execution_details.get("consultation_metadata", {})
        provider = consultation_metadata.get("provider", "")
        
        # Format route info
        route_str = f"{route_used.upper()}"
        if provider:
            route_str += f" ({provider})"
            
        # Performance metrics
        execution_time = execution_details.get("execution_time", 0)
        
        # Clean format for output - only show response in shell UI
        # Debug output is disabled'''
    
    content = re.sub(debug_pattern, debug_repl, content, flags=re.DOTALL)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ Successfully patched {filepath}")
    return True

def patch_cli():
    """
    Patch the CLI to improve response formatting.
    """
    filepath = "core/cli.py"
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Replace the answer extraction code with improved version
    extract_pattern = r'# Extract answer text.*?print\(f"\\n🤖 {default_entity\.title\(\)}: {answer}"\)'
    extract_repl = '''# Extract answer text
                answer = str(response)
                if isinstance(response, dict):
                    if "response" in response:
                        answer = response["response"]
                    elif "result" in response:
                        answer = response["result"]
                
                # Extract routing information
                route_info = ""
                if isinstance(response, dict) and "execution_details" in response:
                    details = response["execution_details"]
                    route = details.get("route_used", "unknown").upper()
                    exec_time = details.get("execution_time", 0)
                    metadata = details.get("consultation_metadata", {})
                    provider = metadata.get("provider", "")
                    
                    # Format route info
                    route_str = f"Route: {route}"
                    if provider:
                        route_str += f" ({provider})"
                    route_str += f", Time: {exec_time:.1f}s"
                    route_info = route_str

                # Print clean response
                print(f"\\n🤖 {default_entity.title()}: {answer}")
                if route_info:
                    print(f"{route_info}")'''
    
    content = re.sub(extract_pattern, extract_repl, content, flags=re.DOTALL)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ Successfully patched {filepath}")
    return True

if __name__ == "__main__":
    print("🔧 Patching Prometheus to improve UI output...")
    patch_base_entity()
    patch_cli()
    print("✅ All patches applied. Restart Prometheus to see changes.")