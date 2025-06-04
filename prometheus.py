#!/usr/bin/env python3
"""
Prometheus Service Launcher

Unified entry point for Aletheia service with multiple frontend modes:
- api: Launch FastAPI REST server
- telegram: Launch Telegram bot  
- shell: Launch interactive terminal shell

All modes share the same singleton Aletheia instance.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    """Main entry point with mode selection."""
    
    parser = argparse.ArgumentParser(
        description="Prometheus Aletheia Service - Multi-Frontend AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Frontend Modes:
  api       Launch FastAPI REST server on port 8000
  telegram  Launch Telegram bot (requires TELEGRAM_TOKEN env var)
  shell     Launch interactive terminal shell
  
Examples:
  python prometheus.py --mode api       # REST API server
  python prometheus.py --mode telegram  # Telegram bot
  python prometheus.py --mode shell     # Interactive shell
  
Environment Variables:
  TELEGRAM_TOKEN  Required for telegram mode
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['api', 'telegram', 'shell'],
        required=True,
        help='Service mode to launch'
    )
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host for API server (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port for API server (default: 8000)'
    )
    
    args = parser.parse_args()
    
    # Check if service is already running
    from core.service.singleton import is_service_running
    
    if is_service_running():
        print(f"⚠️ Warning: Aletheia service may already be running")
        print("   Multiple frontends can share the same instance")
        print("   Continue? [y/N]: ", end="")
        
        try:
            response = input().strip().lower()
            if response not in ['y', 'yes']:
                print("Aborted.")
                return 1
        except KeyboardInterrupt:
            print("\nAborted.")
            return 1
    
    # Launch selected mode
    if args.mode == 'api':
        return launch_api_server(args.host, args.port)
    elif args.mode == 'telegram':
        return launch_telegram_bot()
    elif args.mode == 'shell':
        return launch_shell()
    else:
        print(f"❌ Unknown mode: {args.mode}")
        return 1


def launch_api_server(host: str, port: int) -> int:
    """Launch FastAPI server."""
    try:
        import uvicorn
        print(f"🚀 Starting Aletheia API server on {host}:{port}")
        print(f"📖 API docs will be available at http://{host}:{port}/docs")
        print("Press Ctrl+C to stop")
        
        # Launch uvicorn server
        uvicorn.run(
            "core.service.api_server:app",
            host=host,
            port=port,
            reload=False,  # Disable reload for production
            access_log=True
        )
        
        return 0
        
    except ImportError:
        print("❌ FastAPI/uvicorn not installed. Run: pip install fastapi[all]")
        return 1
    except KeyboardInterrupt:
        print("\n🛑 API server stopped")
        return 0
    except Exception as e:
        print(f"❌ Failed to start API server: {e}")
        return 1


def launch_telegram_bot() -> int:
    """Launch Telegram bot."""
    try:
        import os
        
        # Check for telegram token
        if not os.getenv('TELEGRAM_TOKEN'):
            print("❌ TELEGRAM_TOKEN environment variable not set!")
            print("   Get a bot token from @BotFather on Telegram")
            print("   Then set: export TELEGRAM_TOKEN=your_token_here")
            return 1
        
        print("🤖 Starting Aletheia Telegram bot...")
        print("Press Ctrl+C to stop")
        
        # Launch telegram bot
        from core.service.telegram_bot import main as telegram_main
        asyncio.run(telegram_main())
        
        return 0
        
    except ImportError:
        print("❌ python-telegram-bot not installed. Run: pip install python-telegram-bot")
        return 1
    except KeyboardInterrupt:
        print("\n🛑 Telegram bot stopped")
        return 0
    except Exception as e:
        print(f"❌ Failed to start Telegram bot: {e}")
        return 1


def launch_shell() -> int:
    """Launch interactive shell."""
    try:
        print("🐚 Starting Aletheia interactive shell...")
        
        # Launch shell
        from core.cli import run_shell
        return asyncio.run(run_shell())
        
    except KeyboardInterrupt:
        print("\n🛑 Shell stopped")
        return 0
    except Exception as e:
        print(f"❌ Failed to start shell: {e}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0) 