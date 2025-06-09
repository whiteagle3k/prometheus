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
        """Load Marina's identity, merging register info and config file."""
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
            logger.error(f"❌ Failed to load Marina identity: {e}")
            # Fallback to a minimal, safe configuration
            return register() # Return base registration info on failure


def register() -> dict[str, Any]:
    """Register QA entity with the framework."""
    return {
        "id": "qa",                           # 🔧 Technical ID for registry/API
        "name": {                             # 🏷️ Multilingual human-readable names
            "en": "Marina",
            "ru": "Марина"
        },
        "class": MarinaEntity,                # 🏗️ Implementation class
        "description": "Quality Assurance specialist - detail-oriented, thorough, friendly team player",
        "version": "1.0.0",
        "role": "qa_engineer",                # 🎭 Functional role
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
        "team_position": "quality_guardian",
        "reports_to": "supervisor",           # 🔧 Using technical ID
        "collaborates_with": "developer",    # 🔧 Using technical ID
        "experience_years": 6,
        "personality": "detail_oriented_collaborative_tester",
        "display_info": {
            "icon": "👩‍🔬",
            "color": "#8B5CF6",
            "short_name": "Марина"
        }
    } 