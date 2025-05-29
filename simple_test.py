import asyncio
from aletheia.agent.orchestrator import AletheiaAgent

async def main():
    print("🧪 Testing improvements...")
    agent = AletheiaAgent()
    
    result = await agent.think("привет, меня зовут Игорь")
    print(f"Response: {result['response']}")
    print(f"Route: {result['execution_details']['route_used']}")

asyncio.run(main()) 