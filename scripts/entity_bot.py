#!/usr/bin/env python3
"""
Entity-Specific Telegram Bot Launcher

Launch dedicated Telegram bots for specific entities.
Each bot token corresponds to one entity (e.g., aletheia_bot, tesla_bot).

Usage:
    python scripts/entity_bot.py aletheia TELEGRAM_TOKEN_ALETHEIA
    python scripts/entity_bot.py tesla TELEGRAM_TOKEN_TESLA

Environment variables (alternative):
    TELEGRAM_TOKEN_ALETHEIA=... python scripts/entity_bot.py aletheia
    TELEGRAM_TOKEN_TESLA=... python scripts/entity_bot.py tesla
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Manually load .env file if it exists
env_file = project_root / ".env"
if env_file.exists():
    try:
        # Try to use python-dotenv if available
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print(f"✅ Loaded .env file from {env_file}")
    except ImportError:
        # Fallback: simple manual parsing
        print(f"📄 Loading .env file manually from {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip().strip('"').strip("'")
                    os.environ[key.strip()] = value
else:
    print(f"⚠️ No .env file found at {env_file}")

# Import core modules FIRST to ensure .env file is loaded
from core.frontends.telegram_bot import create_entity_bot
from core.runtime.lifecycle import startup_system


async def main():
    """Main entry point for entity-specific bot."""
    if len(sys.argv) < 2:
        print("❌ Usage: python scripts/entity_bot.py <entity_name> [token]")
        print("   Example: python scripts/entity_bot.py aletheia")
        print("   Example: python scripts/entity_bot.py tesla 123456789:ABCdef...")
        print()
        print("🔑 Token can be provided as:")
        print("   1. Command line argument")
        print("   2. Environment variable TELEGRAM_TOKEN_<ENTITY_UPPER>")
        print("   3. Environment variable TELEGRAM_TOKEN (fallback)")
        return 1

    entity_name = sys.argv[1].lower()
    
    # Try to get token from multiple sources (NOW .env is loaded!)
    token = None
    
    # 1. Command line argument
    if len(sys.argv) >= 3:
        token = sys.argv[2]
        print(f"🔑 Using token from command line argument")
    
    # 2. Entity-specific environment variable
    if not token:
        env_var_name = f"TELEGRAM_TOKEN_{entity_name.upper()}"
        token = os.getenv(env_var_name)
        if token:
            print(f"🔑 Using token from {env_var_name}")
    
    # 3. Generic environment variable
    if not token:
        token = os.getenv("TELEGRAM_TOKEN")
        if token:
            print(f"🔑 Using token from TELEGRAM_TOKEN")
    
    if not token:
        print(f"❌ No Telegram token found for entity '{entity_name}'!")
        print()
        print("🔑 Please provide token via:")
        print(f"   export TELEGRAM_TOKEN_{entity_name.upper()}=your_token_here")
        print("   OR")
        print(f"   python scripts/entity_bot.py {entity_name} your_token_here")
        print()
        print("🔍 Debug: Current environment variables containing 'telegram':")
        for key, value in os.environ.items():
            if 'telegram' in key.lower():
                print(f"   {key}: {value[:20]}..." if len(value) > 20 else f"   {key}: {value}")
        return 1

    print(f"🤖 Starting entity-specific Telegram bot...")
    print(f"🎭 Entity: {entity_name}")
    print(f"🔗 Bot will always respond as {entity_name.capitalize()}")
    print("📱 Commands: /start, /status, /help")
    print("📱 Rate limiting: exponential back-pressure (5s→300s)")
    print("Press Ctrl+C to stop")
    print()

    try:
        # Pre-initialize the entity
        await startup_system([entity_name])
        
        # Create and run entity-specific bot
        await create_entity_bot(token, entity_name)
        
        return 0

    except ImportError as e:
        print(f"❌ Entity '{entity_name}' not found: {e}")
        print("🔍 Available entities in entities/ directory:")
        entities_dir = project_root / "entities"
        if entities_dir.exists():
            for entity_dir in entities_dir.iterdir():
                if entity_dir.is_dir() and not entity_dir.name.startswith('.'):
                    print(f"   - {entity_dir.name}")
        return 1
    except KeyboardInterrupt:
        print(f"\n🛑 Entity-specific bot for {entity_name} stopped")
        return 0
    except Exception as e:
        print(f"❌ Failed to start entity-specific bot: {e}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0) 