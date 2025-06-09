"""
Simplified Aletheia entity for testing purposes.
"""

class AletheiaEntity:
    """A simplified Aletheia entity for testing."""
    
    def __init__(self):
        self.name = "aletheia"
        self.identity_config = {
            "name": {
                "en": "Aletheia",
                "ru": "Алетейя"
            },
            "llm_instructions": "You are a test entity.",
            "translations": {
                "en": {},
                "ru": {}
            }
        }
        print("🚀 Initializing AletheiaEntity entity...")
        print("✅ Loaded identity for Алетейя")
        print("🧠 Using three-tier memory system (Core-Self, User, Environment)")
        print("✅ AletheiaEntity entity initialized")
        print("🧠 Initializing Self-RAG enhancements...")
        print("✅ Self-RAG enhancements initialized")
    
    async def think(self, message, user_id=None):
        print(f"\n🧠 Processing: {message}")
        return f"Aletheia response: {message}"
    
    async def get_status(self):
        return {
            "entity_name": "AletheiaEntity",
            "identity_path": "test/path",
            "conversation_context": True
        }
    
    async def save_state(self):
        pass
    
    async def close(self):
        pass


def register():
    """Register this entity with the Prometheus framework."""
    return {
        "id": "aletheia", 
        "name": {
            "en": "Aletheia",
            "ru": "Алетейя"
        },
        "class": AletheiaEntity,
        "description": "Simplified Aletheia entity for testing",
        "version": "1.0.0"
    } 