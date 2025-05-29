"""Identity configuration loader and validator."""

import json
from pathlib import Path
from typing import Any, Dict

from ..config import config


def load_identity_config() -> Dict[str, Any]:
    """Load the identity configuration from JSON file."""
    identity_file = Path(__file__).parent / "identity.json"
    
    try:
        with open(identity_file, 'r', encoding='utf-8') as f:
            identity_config = json.load(f)
        
        return identity_config
    except FileNotFoundError:
        raise FileNotFoundError(f"Identity configuration not found at {identity_file}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in identity configuration: {e}")


def get_routing_config() -> Dict[str, Any]:
    """Get routing configuration section."""
    identity_config = load_identity_config()
    return identity_config.get("routing_configuration", {})


def get_conversation_config() -> Dict[str, Any]:
    """Get conversation management configuration section."""
    identity_config = load_identity_config()
    return identity_config.get("conversation_management", {})


def get_validation_config() -> Dict[str, Any]:
    """Get validation patterns configuration section."""
    identity_config = load_identity_config()
    return identity_config.get("validation_patterns", {}) 