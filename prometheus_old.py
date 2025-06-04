#!/usr/bin/env python3
"""
Prometheus Framework CLI

A clean command-line interface for running AI entities.

Usage:
    python prometheus.py <entity_name>        # Run entity interactively
    python prometheus.py list                 # List available entities  
    python prometheus.py status <entity_name> # Quick status check
    python prometheus.py --help               # Show help

Examples:
    python prometheus.py aletheia
    poetry run python prometheus.py aletheia
    python prometheus.py list
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def run_entity_interactive(entity_name: str):
    """Run entity in interactive chat mode."""
    
    print(f"🚀 Starting {entity_name.title()} Console Interface")
    print("=" * 60)
    
    try:
        # Import and initialize entity
        from entities import get_entity_class
        
        print(f"📦 Loading {entity_name} entity...")
        EntityClass = get_entity_class(entity_name)
        entity = EntityClass()
        
        # Show initial status
        print(f"\n📊 {entity_name.title()} Status:")
        status = await entity.get_status()
        print(f"  • Entity: {status['entity_name']}")
        print(f"  • Session: {status['session_id']}")
        print(f"  • Memory system: {status['memory_system']}")
        print(f"  • Router health: {status['router_health']['local_llm_available']} (local), {status['router_health']['external_llm_available']} (external)")
        
        print("\n" + "=" * 60)
        print("💬 Interactive Chat Started")
        print("Commands:")
        print("  - Type your message and press Enter")
        print("  - Type 'status' to see entity status")
        print("  - Type 'reset' to reset memory")
        print("  - Type 'quit', 'exit' or Ctrl+C to exit")
        print("=" * 60)
        
        # Interactive chat loop
        while True:
            try:
                # Get user input
                user_input = input(f"\n👤 You: ").strip()
                
                # Handle commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                elif user_input.lower() == 'status':
                    print(f"\n📊 {entity_name.title()} Status:")
                    status = await entity.get_status()
                    print(f"  • Tasks completed: {status['tasks_completed']}")
                    print(f"  • Memory stats: {status['memory_stats']}")
                    print(f"  • Session: {status['session_id']}")
                    continue
                elif user_input.lower() == 'reset':
                    print("\n🗑️ Resetting memory...")
                    await entity.reset_memory()
                    print("✅ Memory reset complete")
                    continue
                elif not user_input:
                    continue
                
                # Get response from entity
                print(f"\n🤔 {entity_name.title()} is thinking...")
                response = await entity.think(user_input)
                print(f"\n🧠 {entity_name.title()}: {response}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                continue
    
    except Exception as e:
        print(f"❌ Failed to start {entity_name}: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


async def list_entities():
    """List all available entities."""
    
    print("🔍 Discovering available entities...")
    
    try:
        from entities import discover_entities
        
        entities = discover_entities()
        
        print(f"\n📋 Available Entities ({len(entities)}):")
        print("=" * 40)
        
        for name, info in entities.items():
            description = info.get('description', 'No description')
            version = info.get('version', '1.0.0')
            capabilities = info.get('capabilities', [])
            
            print(f"🤖 {name}")
            print(f"   Description: {description}")
            print(f"   Version: {version}")
            if capabilities:
                print(f"   Capabilities: {', '.join(capabilities)}")
            print()
        
    except Exception as e:
        print(f"❌ Error discovering entities: {e}")
        return 1
    
    return 0


async def quick_status(entity_name: str):
    """Show quick status for an entity without starting interactive mode."""
    
    print(f"📊 {entity_name.title()} Quick Status")
    print("=" * 40)
    
    try:
        from entities import get_entity_class
        
        print(f"📦 Loading {entity_name} entity...")
        EntityClass = get_entity_class(entity_name)
        entity = EntityClass()
        
        status = await entity.get_status()
        
        print(f"\n✅ Entity: {status['entity_name']}")
        print(f"🆔 Session: {status['session_id']}")
        print(f"🧠 Memory: {status['memory_system']}")
        print(f"🎯 Tasks completed: {status['tasks_completed']}")
        print(f"📡 Local LLM: {'✅' if status['router_health']['local_llm_available'] else '❌'}")
        print(f"🌐 External LLM: {'✅' if status['router_health']['external_llm_available'] else '❌'}")
        
        if status['memory_stats']:
            print(f"💾 Memory stats: {status['memory_stats']}")
        
    except Exception as e:
        print(f"❌ Failed to get status for {entity_name}: {e}")
        return 1
    
    return 0


def main():
    """Main CLI entry point."""
    
    # Handle no arguments case
    if len(sys.argv) == 1:
        print("🚀 Prometheus Framework - AI Entity CLI")
        print("\nUsage:")
        print("  python prometheus.py <entity_name>        # Run entity interactively")
        print("  python prometheus.py list                 # List available entities")
        print("  python prometheus.py status <entity_name> # Quick status check")
        print("  python prometheus.py --help               # Show detailed help")
        print("\nExamples:")
        print("  python prometheus.py aletheia")
        print("  poetry run python prometheus.py aletheia")
        print("  python prometheus.py list")
        return 0
    
    parser = argparse.ArgumentParser(
        description="Prometheus Framework - AI Entity CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python prometheus.py aletheia          # Run Aletheia interactively
  python prometheus.py list              # List available entities
  python prometheus.py status aletheia   # Quick status check
  
  poetry run python prometheus.py aletheia
        """
    )
    
    parser.add_argument(
        'command',
        help='Entity name to run, or command (list, status)'
    )
    
    parser.add_argument(
        'entity',
        nargs='?',
        help='Entity name (required for status command)'
    )
    
    args = parser.parse_args()
    
    # Handle different commands
    if args.command == 'list':
        return asyncio.run(list_entities())
    elif args.command == 'status':
        if not args.entity:
            print("❌ Error: status command requires entity name")
            print("Usage: python prometheus.py status <entity_name>")
            return 1
        return asyncio.run(quick_status(args.entity))
    else:
        # Treat first argument as entity name
        entity_name = args.command
        return asyncio.run(run_entity_interactive(entity_name))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0) 