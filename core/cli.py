"""
Core CLI Module

Provides command-line interface functionality including the shell subcommand.
Uses universal registry system to share entity instances across interfaces.
"""

import asyncio
import signal

from .runtime.registry import get_agent


async def run_shell(default_entity: str = "aletheia") -> int:
    """
    Run interactive shell mode using universal registry.

    Args:
        default_entity: Name of the entity to use (default: aletheia)

    Returns:
        Exit code (0 for success)
    """
    print(f"🐚 {default_entity.title()} Interactive Shell")
    print("=" * 40)
    print("Commands:")
    print("  - Type your message and press Enter")
    print("  - Type 'quit', 'exit' or Ctrl+C to exit")
    print("  - All conversations use user_id='terminal'")
    print("=" * 40)

    agent = None

    async def graceful_shutdown():
        """Handle graceful shutdown with state saving."""
        print("\n🛑 Shutting down shell...")
        if agent and hasattr(agent, "save_state"):
            try:
                print("💾 Saving state...")
                await agent.save_state()
                print("✅ State saved")
            except Exception as e:
                print(f"⚠️ Error saving state: {e}")

        # Note: Registry shutdown is handled by the lifecycle system
        print("👋 Goodbye!")

    # Setup signal handlers for graceful shutdown
    def signal_handler():
        """Handle SIGINT gracefully."""
        asyncio.create_task(graceful_shutdown())

    # Register signal handlers
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())

    try:
        # Get agent instance for the specified entity
        agent = await get_agent(default_entity)

        # Interactive shell loop
        while True:
            try:
                # Get user input
                user_input = input(f"\n🗣️  You: ").strip()

                # Handle exit commands
                if user_input.lower() in ["quit", "exit", "q"]:
                    await graceful_shutdown()
                    break

                # Skip empty input
                if not user_input:
                    continue

                # Process message with the entity
                print("🤔 Thinking...")
                response = await agent.think(user_input, user_id="terminal")

                # Extract answer text
                answer = str(response)
                if isinstance(response, dict) and "result" in response:
                    answer = response["result"]

                print(f"\n🤖 {default_entity.title()}: {answer}")

            except KeyboardInterrupt:
                await graceful_shutdown()
                break
            except EOFError:
                await graceful_shutdown()
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
        "shell",
        help="Start interactive shell with specified entity"
    )
    shell_parser.add_argument(
        "--entity",
        default="aletheia",
        help="Entity to use in shell (default: aletheia)"
    )
    shell_parser.set_defaults(func=lambda args: asyncio.run(run_shell(args.entity)))
