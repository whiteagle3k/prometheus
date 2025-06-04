"""Identity configuration validation utilities."""

import json
from pathlib import Path
from typing import Any


def validate_identity_schema(identity_data: dict[str, Any]) -> list[str]:
    """Validate identity configuration schema.

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Required top-level fields
    required_fields = ["meta", "name", "primary_language", "identity"]
    for field in required_fields:
        if field not in identity_data:
            errors.append(f"Missing required field: {field}")

    # Validate meta section
    if "meta" in identity_data:
        meta = identity_data["meta"]
        if not isinstance(meta.get("version"), str):
            errors.append("meta.version must be a string")
        if not isinstance(meta.get("created_at"), str):
            errors.append("meta.created_at must be a string")

    # Validate identity section
    if "identity" in identity_data:
        identity_section = identity_data["identity"]
        if not isinstance(identity_section.get("summary"), str):
            errors.append("identity.summary must be a string")
        if not isinstance(identity_section.get("personality"), list):
            errors.append("identity.personality must be a list")

    # Validate language support
    primary_lang = identity_data.get("primary_language")
    if primary_lang not in ["en", "ru"]:
        errors.append("primary_language must be 'en' or 'ru'")

    supported_langs = identity_data.get("supported_languages", [])
    if not isinstance(supported_langs, list) or not supported_langs:
        errors.append("supported_languages must be a non-empty list")

    # Validate operational guidelines
    if "operational_guidelines" in identity_data:
        guidelines = identity_data["operational_guidelines"]
        if "routing_policy" in guidelines:
            routing = guidelines["routing_policy"]
            thresholds = routing.get("thresholds", {})
            if not isinstance(thresholds.get("max_tokens_local"), int):
                errors.append("routing_policy.thresholds.max_tokens_local must be an integer")

    return errors


def validate_identity_file(identity_path: Path) -> list[str]:
    """Validate identity configuration file.

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check file exists
    if not identity_path.exists():
        return [f"Identity file not found: {identity_path}"]

    # Parse JSON
    try:
        with open(identity_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON in identity file: {e}"]
    except Exception as e:
        return [f"Error reading identity file: {e}"]

    # Validate schema
    schema_errors = validate_identity_schema(data)
    errors.extend(schema_errors)

    return errors


def check_identity_completeness(identity_instance) -> dict[str, Any]:
    """Check completeness of a loaded identity instance.

    Returns:
        Dictionary with completeness information
    """
    completeness = {
        "is_complete": True,
        "missing_components": [],
        "warnings": [],
        "score": 0
    }

    # Check required components
    components = [
        ("name", identity_instance.name),
        ("summary", identity_instance.personality.summary),
        ("personality_traits", identity_instance.personality.personality),
        ("core_values", identity_instance.core_values),
        ("llm_instructions", identity_instance.llm_instructions),
        ("routing_threshold", identity_instance.get_routing_threshold()),
        ("model_path", identity_instance.get_model_path())
    ]

    total_components = len(components)
    complete_components = 0

    for name, value in components:
        if value and (not isinstance(value, list | str) or len(str(value)) > 0):
            complete_components += 1
        else:
            completeness["missing_components"].append(name)
            completeness["is_complete"] = False

    # Calculate score
    completeness["score"] = (complete_components / total_components) * 100

    # Add warnings for common issues
    if len(identity_instance.personality.personality) < 3:
        completeness["warnings"].append("Less than 3 personality traits defined")

    if len(identity_instance.core_values) < 3:
        completeness["warnings"].append("Less than 3 core values defined")

    if identity_instance.get_routing_threshold() < 500:
        completeness["warnings"].append("Routing threshold might be too low")

    return completeness
