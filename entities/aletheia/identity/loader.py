"""Identity configuration loader and validator."""

import json
from pathlib import Path
from typing import Any


def load_identity_config() -> dict[str, Any]:
    """Load the identity configuration from JSON file."""
    identity_file = Path(__file__).parent / "identity.json"

    try:
        with open(identity_file, encoding="utf-8") as f:
            return json.load(f)

    except FileNotFoundError:
        msg = f"Identity configuration not found at {identity_file}"
        raise FileNotFoundError(msg)
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON in identity configuration: {e}"
        raise ValueError(msg)


def get_routing_config() -> dict[str, Any]:
    """Get routing configuration section."""
    identity_config = load_identity_config()
    return identity_config.get("routing_configuration", {})


def get_conversation_config() -> dict[str, Any]:
    """Get conversation management configuration section."""
    identity_config = load_identity_config()
    return identity_config.get("conversation_management", {})


def get_validation_config() -> dict[str, Any]:
    """Get validation patterns configuration section."""
    identity_config = load_identity_config()
    return identity_config.get("validation_patterns", {})


def get_external_llm_config() -> dict[str, Any]:
    """Get external LLM configuration section."""
    identity_config = load_identity_config()
    return identity_config.get("external_llms", {})


def get_provider_config(provider_name: str) -> dict[str, Any]:
    """Get configuration for a specific external LLM provider."""
    external_config = get_external_llm_config()
    providers = external_config.get("providers", {})
    return providers.get(provider_name, {})
