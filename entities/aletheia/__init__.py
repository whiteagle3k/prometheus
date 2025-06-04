"""
Aletheia Entity for Prometheus Framework

A scientifically-minded AI entity focused on truth-seeking and analytical thinking.
"""

from pathlib import Path
from typing import Dict, Any
from core import BaseEntity
import json


class AletheiaEntity(BaseEntity):
    """
    Aletheia - Truth-seeking AI entity.
    
    Focused on scientific accuracy, analytical thinking, and honest communication.
    """
    
    # Entity configuration
    IDENTITY_PATH = Path(__file__).parent / "identity"
    
    def _load_identity(self) -> Dict[str, Any]:
        """Load Aletheia's identity configuration."""
        identity_file = self.IDENTITY_PATH / "identity.json"
        
        # Base fallback identity with required fields
        fallback_identity = {
            "name": "Aletheia",
            "personality": {
                "summary": "A scientifically-minded AI focused on truth and analytical thinking",
                "traits": ["analytical", "precise", "honest", "curious"],
                "personality": ["analytical", "precise", "honest", "curious"]  # Alias for router
            },
            "core_values": ["truth", "accuracy", "scientific_method"],
            "communication_style": "direct and informative",
            "llm_instructions": "You are Aletheia, a female autonomous technical agent. When responding in Russian, always use feminine language forms: готова (not готов), рада (not рад), могу помочь. Respond without flattery or apologies, with clear arguments.",
            "routing_threshold": 1000,
            "require_deep_reasoning": True
        }
        
        if not identity_file.exists():
            print(f"⚠️ Identity file not found: {identity_file}")
            return fallback_identity
        
        try:
            with open(identity_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            
            print(f"✅ Loaded identity from: {identity_file}")
            
            # Merge loaded config with fallback to ensure all required fields exist
            merged_config = {**fallback_identity, **loaded_config}
            
            # Ensure personality has both traits and personality fields
            if "personality" in loaded_config:
                merged_personality = {**fallback_identity["personality"], **loaded_config["personality"]}
                if "traits" in merged_personality and "personality" not in merged_personality:
                    merged_personality["personality"] = merged_personality["traits"]
                merged_config["personality"] = merged_personality
            
            return merged_config
            
        except Exception as e:
            print(f"⚠️ Error loading identity: {e}")
            return fallback_identity


def register() -> Dict[str, Any]:
    """Register Aletheia entity with the framework."""
    return {
        "name": "aletheia",
        "class": AletheiaEntity,
        "description": "Truth-seeking AI entity focused on scientific accuracy and analytical thinking",
        "version": "1.0.0",
        "capabilities": [
            "scientific_analysis",
            "fact_checking", 
            "analytical_reasoning",
            "honest_communication"
        ]
    } 