#!/usr/bin/env python3
"""
Prometheus Service Launcher

Unified entry point for multi-entity AI service with multiple frontend modes:
- api: Launch FastAPI REST server  
- telegram: Launch Telegram bot
- shell: Launch interactive terminal shell

All modes use the universal runtime registry to support multiple entities.
"""

import argparse
import asyncio
import signal
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def setup_signal_handlers():
    """Setup graceful shutdown signal handlers."""
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}, initiating graceful shutdown...")
        # Import here to avoid circular imports
        from core.runtime.lifecycle import shutdown_system
        asyncio.create_task(shutdown_system())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main entry point with mode selection."""
    
    parser = argparse.ArgumentParser(
        description="Prometheus Universal AI Service - Multi-Entity Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Frontend Modes:
  api       Launch FastAPI REST server on port 8000
  telegram  Launch Telegram bot (requires TELEGRAM_TOKEN env var)
  shell     Launch interactive terminal shell
  
Entity Support:
  --entity <name>     Specify default entity (default: aletheia)
  --entities <list>   Pre-initialize multiple entities
  
Examples:
  python prometheus.py api                           # API with aletheia
  python prometheus.py api --entity prometheus      # API with prometheus entity
  python prometheus.py telegram --entities aletheia,teslabot  # Telegram with multiple entities
  python prometheus.py shell --entity aletheia      # Shell with aletheia
  
Environment Variables:
  TELEGRAM_TOKEN  Required for telegram mode
  AUTONOMY_ENABLED  Enable auto-snapshots (default: false)
        """
    )
    
    parser.add_argument(
        'mode',
        choices=['api', 'telegram', 'shell'],
        help='Service mode to launch'
    )
    
    parser.add_argument(
        '--entity',
        default='aletheia',
        help='Default entity to use (default: aletheia)'
    )
    
    parser.add_argument(
        '--entities',
        help='Comma-separated list of entities to pre-initialize'
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
    
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='Number of uvicorn workers (must be 1 for registry compatibility)'
    )
    
    args = parser.parse_args()
    
    # Validate workers for registry compatibility
    if args.mode == 'api' and args.workers != 1:
        print("⚠️ Warning: Multiple workers break registry pattern")
        print("   Setting workers=1 for registry compatibility")
        args.workers = 1
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Prepare entities list
    entities_to_init = []
    if args.entities:
        entities_to_init = [e.strip() for e in args.entities.split(',')]
    else:
        entities_to_init = [args.entity]
    
    # Check if any agents are already running
    from core.runtime.registry import get_running_agents
    
    running = get_running_agents()
    if running:
        print(f"ℹ️ Info: Agents already running: {running}")
        print("   Multiple frontends can share the same registry")
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
        return launch_api_server(args.host, args.port, args.workers, entities_to_init)
    elif args.mode == 'telegram':
        return launch_telegram_bot(entities_to_init)
    elif args.mode == 'shell':
        return launch_shell(args.entity)
    else:
        print(f"❌ Unknown mode: {args.mode}")
        return 1


def launch_api_server(host: str, port: int, workers: int = 1, entities: list = None) -> int:
    """Launch FastAPI server with universal entity support."""
    try:
        import uvicorn
        
        if entities is None:
            entities = ["aletheia"]
        
        print(f"🚀 Starting Prometheus API server on {host}:{port}")
        print(f"🤖 Pre-initializing entities: {', '.join(entities)}")
        print(f"📖 API docs will be available at http://{host}:{port}/docs")
        print(f"🔗 Registry info: http://{host}:{port}/v1/registry")
        print(f"⚙️ Workers: {workers} (registry compatibility)")
        print(f"📝 Structured JSON logging enabled")
        print("   Example: curl 'http://localhost:8000/v1/chat?entity=aletheia' \\")
        print("           -H 'Content-Type: application/json' \\")
        print("           -d '{\"user_id\":\"test\",\"message\":\"Hello\"}'")
        print("Press Ctrl+C to stop")
        
        # Pre-initialize entities
        async def init_entities():
            from core.runtime.lifecycle import startup_system
            await startup_system(entities)
        
        # Run pre-initialization
        asyncio.run(init_entities())
        
        # Launch uvicorn server
        uvicorn.run(
            "core.frontends.api_server:app",
            host=host,
            port=port,
            workers=workers,  # Always 1 for registry compatibility
            reload=False,     # Disable reload for production
            access_log=False, # Use structured logging
            log_level="info"
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


def launch_telegram_bot(entities: list = None) -> int:
    """Launch Telegram bot with multi-entity support."""
    try:
        import os
        
        # Check for telegram token
        if not os.getenv('TELEGRAM_TOKEN'):
            print("❌ TELEGRAM_TOKEN environment variable not set!")
            print("   Get a bot token from @BotFather on Telegram")
            print("   Then set: export TELEGRAM_TOKEN=your_token_here")
            return 1
        
        if entities is None:
            entities = ["aletheia"]
        
        print("🤖 Starting Prometheus universal Telegram bot...")
        print(f"🤖 Pre-initializing entities: {', '.join(entities)}")
        print("📱 Commands: /use <entity>, /entities, /status")
        print("📱 Rate limiting: exponential back-pressure (5s→300s)")
        print("Press Ctrl+C to stop")
        
        # Pre-initialize entities and launch bot
        async def run_bot():
            from core.runtime.lifecycle import startup_system
            await startup_system(entities)
            
            from core.frontends.telegram_bot import main as telegram_main
            await telegram_main()
        
        asyncio.run(run_bot())
        
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


def launch_shell(entity: str = "aletheia") -> int:
    """Launch interactive shell with specified entity."""
    try:
        print(f"🐚 Starting Prometheus interactive shell...")
        print(f"🤖 Default entity: {entity}")
        print("💾 Graceful shutdown with state saving enabled")
        print("💡 Use --entity <name> to change default entity")
        
        # Launch shell with entity parameter
        async def run_shell():
            from core.runtime.lifecycle import startup_system
            await startup_system([entity])
            
            from core.cli import run_shell
            return await run_shell(default_entity=entity)
        
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