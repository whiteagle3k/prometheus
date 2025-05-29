"""Configuration loader for text processors."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ProcessorConfig:
    """Configuration for a text processor."""
    name: str
    enabled: bool = True
    parameters: Dict[str, Any] = None
    patterns: List[str] = None
    thresholds: Dict[str, float] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.patterns is None:
            self.patterns = []
        if self.thresholds is None:
            self.thresholds = {}


class ProcessorConfigLoader:
    """Loads processor configurations from JSON files."""
    
    def __init__(self, config_dir: Path = None):
        """Initialize config loader."""
        if config_dir is None:
            config_dir = Path(__file__).parent / "configs"
        self.config_dir = config_dir
        self._cache: Dict[str, ProcessorConfig] = {}
    
    def load_config(self, processor_name: str) -> ProcessorConfig:
        """Load configuration for a specific processor."""
        if processor_name in self._cache:
            return self._cache[processor_name]
        
        config_file = self.config_dir / f"{processor_name}.json"
        
        if not config_file.exists():
            # Return default config
            config = ProcessorConfig(name=processor_name)
        else:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                config = ProcessorConfig(
                    name=processor_name,
                    enabled=data.get("enabled", True),
                    parameters=data.get("parameters", {}),
                    patterns=data.get("patterns", []),
                    thresholds=data.get("thresholds", {})
                )
            except Exception as e:
                print(f"Warning: Failed to load config for {processor_name}: {e}")
                config = ProcessorConfig(name=processor_name)
        
        self._cache[processor_name] = config
        return config
    
    def load_all_configs(self) -> Dict[str, ProcessorConfig]:
        """Load all available processor configs."""
        configs = {}
        
        if not self.config_dir.exists():
            return configs
        
        for config_file in self.config_dir.glob("*.json"):
            processor_name = config_file.stem
            configs[processor_name] = self.load_config(processor_name)
        
        return configs
    
    def reload_config(self, processor_name: str) -> ProcessorConfig:
        """Reload a specific processor config (clear cache first)."""
        if processor_name in self._cache:
            del self._cache[processor_name]
        return self.load_config(processor_name)
    
    def clear_cache(self):
        """Clear the configuration cache."""
        self._cache.clear()


# Global config loader instance
_config_loader = ProcessorConfigLoader()


def get_processor_config(processor_name: str) -> ProcessorConfig:
    """Get configuration for a processor."""
    return _config_loader.load_config(processor_name)


def reload_processor_config(processor_name: str) -> ProcessorConfig:
    """Reload configuration for a processor."""
    return _config_loader.reload_config(processor_name)


def set_config_directory(config_dir: Path):
    """Set the configuration directory."""
    global _config_loader
    _config_loader = ProcessorConfigLoader(config_dir) 