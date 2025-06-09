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
        """Load Vasya's identity, merging register info and config file."""
        try:
            # 1. Get base registration info (ID, multilingual names)
            reg_info = register()
            
            # 2. Load detailed config from JSON
            identity_file = self.IDENTITY_PATH / "identity.json"
            if not identity_file.exists():
                raise FileNotFoundError(f"Identity file not found: {identity_file}")
            
            with open(identity_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 3. Merge them: config file overrides everything except id and name
            final_config = {**config, **reg_info}
            
            # 4. Ensure ID from register() matches ID in file for consistency
            if 'id' in config and config['id'] != reg_info['id']:
                logger.warning(
                    f"ID mismatch between register() ('{reg_info['id']}') and "
                    f"identity.json ('{config['id']}'). Using ID from register()."
                )
            
            # Use the simple name for logging, but keep the dict for the app
            log_name = reg_info.get('name', {}).get('ru', reg_info.get('id'))
            logger.info(f"✅ Loaded identity for {log_name}")
            
            return final_config
            
        except Exception as e:
            logger.error(f"❌ Failed to load Vasya identity: {e}")
            # Fallback to a minimal, safe configuration
            return register() # Return base registration info on failure


def register() -> dict[str, Any]:
    """Register Developer entity with the framework."""
    return {
        "id": "developer",                     # 🔧 Technical ID for registry/API  
        "name": {                             # 🏷️ Multilingual human-readable names
            "en": "Vasya", 
            "ru": "Вася"
        },
        "class": VasyaEntity,                 # 🏗️ Implementation class
        "description": "Mid-level developer with 10 years experience - proactive, obedient, eager to work",
        "version": "1.0.0",
        "role": "developer",                  # 🎭 Functional role
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
        "team_position": "implementer",
        "reports_to": "supervisor",           # 🔧 Using technical ID
        "experience_years": 10,
        "personality": "enthusiastic_proactive_implementer",
        "display_info": {
            "icon": "👨‍💻",
            "color": "#10B981",
            "short_name": "Вася"
        }
    } 