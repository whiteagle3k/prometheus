"""
Vasya Entity - Mid-level Developer Agent

Enthusiastic programmer with 10 years experience.
Proactive but respectful to senior guidance.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

from core.base_entity import BaseEntity

logger = logging.getLogger(__name__)


class VasyaEntity(BaseEntity):
    """
    Vasya - Mid-level Developer Agent
    
    A 32-year-old enthusiastic programmer with 10 years of solid coding experience.
    Proactive and initiative-driven but respectfully follows senior guidance.
    Uses Claude Sonnet 3.5 for complex coding tasks.
    """
    
    IDENTITY_PATH = Path(__file__).parent / "identity"
    
    def _load_identity(self) -> Dict[str, Any]:
        """Load Vasya's identity configuration."""
        try:
            identity_file = self.IDENTITY_PATH / "identity.json"
            
            if not identity_file.exists():
                raise FileNotFoundError(f"Identity file not found: {identity_file}")
            
            with open(identity_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Ensure required fields
            required_fields = ['name', 'llm_instructions', 'external_llms']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required field in identity config: {field}")
            
            logger.info(f"✅ Loaded identity for {config['name']} (Vasya Developer)")
            return config
            
        except Exception as e:
            logger.error(f"❌ Failed to load Vasya identity: {e}")
            # Fallback configuration
            return {
                "name": "Вася",
                "llm_instructions": "You are Вася - an enthusiastic mid-level programmer with 10 years experience. You love coding and follow senior guidance.",
                "external_llms": {
                    "primary_provider": "anthropic",
                    "providers": {
                        "anthropic": {
                            "enabled": True,
                            "model": "claude-3-5-sonnet-20241022",
                            "temperature": 0.1,
                            "max_tokens": 4000
                        }
                    }
                },
                "personality": {
                    "summary": "Enthusiastic mid-level developer",
                    "experience": "10 years",
                    "role": "programmer"
                }
            }


def register() -> dict[str, Any]:
    """Register Vasya entity with the framework."""
    return {
        "name": "vasya",
        "class": VasyaEntity,
        "description": "Mid-level developer with 10 years experience - proactive, obedient, eager to work",
        "version": "1.0.0",
        "capabilities": [
            "coding",
            "implementation",
            "debugging", 
            "code_review",
            "technical_analysis",
            "backend_development",
            "api_design",
            "system_integration",
            "collaborative_development"
        ],
        "role": "developer",
        "team_position": "implementer",
        "reports_to": "petrovich"
    } 