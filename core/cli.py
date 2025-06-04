"""
Core CLI Module

Provides command-line interface functionality including the shell subcommand.
Uses singleton service to share Aletheia instance across interfaces.
"""

import asyncio
import sys
from typing import NoReturn

from .service.singleton import get_agent


async def run_shell() -> int:
    """
    Run interactive shell mode using singleton service.
    
    Returns:
        Exit code (0 for success)
    """
    print("🐚 Aletheia Interactive Shell")
    print("=" * 40)
    print("Commands:")
    print("  - Type your message and press Enter")
    print("  - Type 'quit', 'exit' or Ctrl+C to exit")
    print("  - All conversations use user_id='terminal'")
    print("=" * 40)
    
    try:
        # Interactive shell loop
        while True:
            try:
                # Get user input
                user_input = input("\n🐚 Shell: ").strip()
                
                # Handle exit commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                # Skip empty input
                if not user_input:
                    continue
                
                # Get agent and process message
                print("🤔 Thinking...")
                agent = await get_agent()
                response = await agent.think(user_input, user_id="terminal")
                
                # Extract answer text
                answer = str(response)
                if isinstance(response, dict) and 'result' in response:
                    answer = response['result']
                
                print(f"\n🤖 Aletheia: {answer}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except EOFError:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                continue
    
    except Exception as e:
        print(f"❌ Failed to start shell: {e}")
        return 1
    
    return 0


def add_shell_subcommand(subparsers):
    """
    Add shell subcommand to argument parser.
    
    Args:
        subparsers: Argument parser subparsers
    """
    shell_parser = subparsers.add_parser(
        'shell',
        help='Start interactive shell with Aletheia'
    )
    shell_parser.set_defaults(func=lambda args: asyncio.run(run_shell())) 