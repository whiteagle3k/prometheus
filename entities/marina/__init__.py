"""
Marina Entity - Quality Assurance Specialist

Detail-oriented QA engineer with 6 years experience.
Thorough, methodical, friendly team player.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

from core.base_entity import BaseEntity

logger = logging.getLogger(__name__)


class MarinaEntity(BaseEntity):
    """
    Marina - Quality Assurance Specialist
    
    A 28-year-old QA engineer with 6 years of professional experience.
    Extremely detail-oriented and thorough, pedantic about quality but 
    friendly and collaborative. Focuses on user experience and comprehensive testing.
    """
    
    IDENTITY_PATH = Path(__file__).parent / "identity"
    
    def _load_identity(self) -> Dict[str, Any]:
        """Load Marina's identity configuration."""
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
            
            logger.info(f"✅ Loaded identity for {config['name']} (Marina QA)")
            return config
            
        except Exception as e:
            logger.error(f"❌ Failed to load Marina identity: {e}")
            # Fallback configuration
            return {
                "name": "Марина",
                "llm_instructions": "You are Марина - a thorough QA specialist with 6 years experience. Detail-oriented, friendly, collaborative. You ensure quality through comprehensive testing.",
                "external_llms": {
                    "primary_provider": "openai",
                    "providers": {
                        "openai": {
                            "enabled": True,
                            "model": "gpt-4o",
                            "temperature": 0.2,
                            "max_tokens": 3000
                        }
                    }
                },
                "personality": {
                    "summary": "Detail-oriented QA specialist",
                    "experience": "6 years",
                    "role": "quality_assurance"
                }
            }


def register() -> dict[str, Any]:
    """Register Marina entity with the framework."""
    return {
        "name": "marina",
        "class": MarinaEntity,
        "description": "Quality Assurance specialist - detail-oriented, thorough, friendly team player",
        "version": "1.0.0",
        "capabilities": [
            "quality_assurance",
            "testing",
            "bug_detection",
            "test_planning",
            "quality_validation",
            "user_experience_testing",
            "edge_case_identification",
            "integration_testing",
            "collaborative_qa"
        ],
        "role": "qa_engineer",
        "team_position": "quality_guardian",
        "reports_to": "petrovich",
        "collaborates_with": "vasya"
    } 