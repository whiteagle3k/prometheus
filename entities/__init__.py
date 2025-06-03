"""
Entities Module for Prometheus Framework

Contains entity implementations that use the core framework.
Provides entity discovery and registration capabilities.
"""

import importlib
from pathlib import Path
from typing import Dict, Type, Any


def discover_entities() -> Dict[str, Dict[str, Any]]:
    """
    Discover all available entities in the entities directory.
    
    Returns dictionary mapping entity names to their registration info.
    """
    entities = {}
    entities_dir = Path(__file__).parent
    
    # Look for entity directories
    for entity_path in entities_dir.iterdir():
        if entity_path.is_dir() and not entity_path.name.startswith('_'):
            try:
                # Try to import the entity module
                entity_module = importlib.import_module(f"entities.{entity_path.name}")
                
                # Check if it has a register function
                if hasattr(entity_module, 'register'):
                    registration = entity_module.register()
                    entities[registration['name']] = registration
                    
            except ImportError as e:
                print(f"⚠️ Could not import entity {entity_path.name}: {e}")
                continue
    
    return entities


def get_entity_class(entity_name: str) -> Type:
    """Get the entity class for the given entity name."""
    entities = discover_entities()
    
    if entity_name not in entities:
        available = list(entities.keys())
        raise ValueError(f"Entity '{entity_name}' not found. Available: {available}")
    
    return entities[entity_name]['class']


# Auto-discover entities on import
available_entities = discover_entities()

__all__ = ["discover_entities", "get_entity_class", "available_entities"] 