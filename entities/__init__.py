"""
Entities Module for Prometheus Framework

Contains entity implementations that use the core framework.
Provides entity discovery and registration capabilities with proper separation
of technical IDs and human-readable names with multi-language support.
"""

import importlib
from pathlib import Path
from typing import Any


def get_localized_name(name_data: Any, language: str = "en") -> str:
    """
    Get localized name with fallback to English.
    
    Args:
        name_data: Name data (string or dict with language keys)
        language: Target language code (default: "en")
        
    Returns:
        Localized name string
    """
    # Handle legacy string format
    if isinstance(name_data, str):
        return name_data
    
    # Handle dictionary format
    if isinstance(name_data, dict):
        # Try requested language first
        if language in name_data:
            return name_data[language]
        
        # Fallback to English
        if "en" in name_data:
            return name_data["en"]
        
        # Fallback to any available language
        if name_data:
            return list(name_data.values())[0]
    
    # Fallback for any other case
    return str(name_data)


def discover_entities() -> dict[str, dict[str, Any]]:
    """
    Discover all available entities in the entities directory.

    Returns dictionary mapping entity IDs to their registration info.
    Each entity provides:
    - id: Technical identifier for registry/API
    - name: Human-readable name(s) - can be string or dict with language codes
    - class: Entity class for instantiation
    - module_path: Python module path
    - description: Entity description
    """
    entities = {}
    entities_dir = Path(__file__).parent

    # Look for entity directories
    for entity_path in entities_dir.iterdir():
        if entity_path.is_dir() and not entity_path.name.startswith("_"):
            try:
                # Try to import the entity module
                module_name = entity_path.name
                entity_module = importlib.import_module(f"entities.{module_name}")

                # Check if it has a register function
                if hasattr(entity_module, "register"):
                    registration = entity_module.register()
                    
                    # Validate registration structure
                    if not isinstance(registration, dict):
                        print(f"⚠️ Invalid registration for {module_name}: must return dict")
                        continue
                        
                    if "id" not in registration:
                        print(f"⚠️ Invalid registration for {module_name}: missing 'id' field")
                        continue
                        
                    if "class" not in registration:
                        print(f"⚠️ Invalid registration for {module_name}: missing 'class' field")
                        continue
                    
                    # Add metadata for registry
                    entity_id = registration["id"]
                    registration["module_path"] = f"entities.{module_name}"
                    registration["module_name"] = module_name
                    
                    entities[entity_id] = registration
                    
            except ImportError as e:
                print(f"⚠️ Could not import entity {entity_path.name}: {e}")
                continue
            except Exception as e:
                print(f"⚠️ Error registering entity {entity_path.name}: {e}")
                continue

    return entities


def get_entity_class(entity_id: str) -> type:
    """Get the entity class for the given entity ID."""
    entities = discover_entities()

    if entity_id not in entities:
        available = list(entities.keys())
        msg = f"Entity '{entity_id}' not found. Available: {available}"
        raise ValueError(msg)

    return entities[entity_id]["class"]


def get_entity_info(entity_id: str) -> dict[str, Any]:
    """Get full entity information for the given entity ID."""
    entities = discover_entities()

    if entity_id not in entities:
        available = list(entities.keys())
        msg = f"Entity '{entity_id}' not found. Available: {available}"
        raise ValueError(msg)

    return entities[entity_id]


def list_entity_ids() -> list[str]:
    """Get list of all available entity IDs."""
    return list(discover_entities().keys())


def list_entity_names(language: str = "en") -> dict[str, str]:
    """
    Get mapping of entity IDs to localized human names.
    
    Args:
        language: Language code for localization (default: "en")
        
    Returns:
        Dict mapping entity IDs to localized names
    """
    entities = discover_entities()
    return {
        entity_id: get_localized_name(info.get("name", entity_id), language) 
        for entity_id, info in entities.items()
    }


def get_entity_name(entity_id: str, language: str = "en") -> str:
    """
    Get localized name for specific entity.
    
    Args:
        entity_id: Technical ID of the entity
        language: Language code for localization (default: "en")
        
    Returns:
        Localized entity name
    """
    try:
        entity_info = get_entity_info(entity_id)
        return get_localized_name(entity_info.get("name", entity_id), language)
    except ValueError:
        return entity_id  # Fallback to ID if entity not found


# Auto-discover entities on import
available_entities = discover_entities()

__all__ = [
    "discover_entities", 
    "get_entity_class", 
    "get_entity_info",
    "list_entity_ids",
    "list_entity_names",
    "get_entity_name",
    "get_localized_name",
    "available_entities"
]
