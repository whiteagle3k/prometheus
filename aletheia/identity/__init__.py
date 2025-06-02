"""Identity management for Aletheia agent."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

# Import submodules
from .validator import validate_identity_file, check_identity_completeness
from .templates import AGENT_TEMPLATES, create_base_identity_template


@dataclass
class IdentityMeta:
    """Metadata about the identity configuration."""
    snapshot_id: str
    created_at: str
    version: str


@dataclass
class PersonalityProfile:
    """Core personality and identity information."""
    summary: str
    personality: List[str]


@dataclass
class RoutingPolicy:
    """Policy for routing between local and external LLMs."""
    description: str
    max_tokens_local: int
    requires_deep_reasoning: bool


@dataclass
class MemoryManagement:
    """Memory management configuration."""
    storage: str
    summarisation: str
    retention: str


@dataclass
class OperationalGuidelines:
    """Operational guidelines and policies."""
    routing_policy: RoutingPolicy
    memory_management: MemoryManagement


@dataclass
class ModulePaths:
    """Paths to various modules and models."""
    local_llm_binary: str
    local_model_gguf: str
    memory_dir: str
    performance_config: Optional[Dict[str, Any]] = None


@dataclass
class SampleMemory:
    """Sample memory entry."""
    role: str
    content: str
    timestamp: str


class Identity:
    """Manages Aletheia's identity configuration with English-primary design."""
    
    def __init__(self, identity_path: Optional[Path] = None):
        """Initialize identity from JSON file."""
        self.identity_path = identity_path or Path("aletheia/identity/identity.json")
        self._load_identity()
    
    def _load_identity(self) -> None:
        """Load identity configuration from JSON file."""
        try:
            with open(self.identity_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Parse metadata
            meta_data = data.get("meta", {})
            self.meta = IdentityMeta(
                snapshot_id=meta_data.get("snapshot_id", ""),
                created_at=meta_data.get("created_at", ""),
                version=meta_data.get("version", "0.2.0")
            )
            
            # Basic identity information - now English-primary
            self.name: str = data.get("name", "Aletheia")
            self.primary_language: str = data.get("primary_language", "en")
            self.supported_languages: List[str] = data.get("supported_languages", ["en", "ru"])
            
            # Core personality profile (English)
            identity_data = data.get("identity", {})
            self.personality = PersonalityProfile(
                summary=identity_data.get("summary", ""),
                personality=identity_data.get("personality", [])
            )
            
            # Core values and goals (English)
            self.core_values: List[str] = data.get("core_values", [])
            self.goals: List[str] = data.get("goals", [])
            self.constitution: List[str] = data.get("constitution", [])
            
            # Operational guidelines
            guidelines_data = data.get("operational_guidelines", {})
            routing_data = guidelines_data.get("routing_policy", {})
            memory_data = guidelines_data.get("memory_management", {})
            
            self.operational_guidelines = OperationalGuidelines(
                routing_policy=RoutingPolicy(
                    description=routing_data.get("description", ""),
                    max_tokens_local=routing_data.get("thresholds", {}).get("max_tokens_local", 1024),
                    requires_deep_reasoning=routing_data.get("thresholds", {}).get("requires_deep_reasoning", True)
                ),
                memory_management=MemoryManagement(
                    storage=memory_data.get("storage", "ChromaDB (vector)"),
                    summarisation=memory_data.get("summarisation", ""),
                    retention=memory_data.get("retention", "")
                )
            )
            
            # Module paths
            paths_data = data.get("module_paths", {})
            self.module_paths = ModulePaths(
                local_llm_binary=paths_data.get("local_llm_binary", ""),
                local_model_gguf=paths_data.get("local_model_gguf", ""),
                memory_dir=paths_data.get("memory_dir", "storage/chroma"),
                performance_config=paths_data.get("performance_config", None)
            )
            
            # Sample memories
            sample_memories_data = data.get("sample_memories", [])
            self.sample_memories = [
                SampleMemory(
                    role=mem.get("role", ""),
                    content=mem.get("content", ""),
                    timestamp=mem.get("timestamp", "")
                )
                for mem in sample_memories_data
            ]
            
            # LLM instructions (English primary)
            self.llm_instructions: str = data.get("llm_instructions", "")
            
            # Translation data
            self.translations: Dict[str, Any] = data.get("translations", {})
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Identity file not found: {self.identity_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in identity file: {e}")
    
    def get_system_prompt(self, language: Optional[str] = None) -> str:
        """Get system prompt based on identity configuration.
        
        Uses language-specific instructions for better performance in target language.
        """
        target_language = language or self.primary_language
        prompt_parts = []
        
        if target_language == "ru" and "ru" in self.translations:
            # Use Russian identity and instructions for Russian prompts
            ru_data = self.translations["ru"]
            ru_identity = ru_data.get("identity", {})
            
            # Core identity in Russian
            ru_summary = ru_identity.get("summary", self.personality.summary)
            prompt_parts.append(f"Ты — {self.name}, {ru_summary}.")
            
            # Russian personality traits
            ru_personality = ru_identity.get("personality", self.personality.personality)
            if ru_personality:
                traits_text = ", ".join(ru_personality[:3])
                prompt_parts.append(f"Ключевые черты: {traits_text}.")
            
            # Russian core values
            ru_values = ru_data.get("core_values", self.core_values)
            if ru_values:
                values_text = ", ".join(ru_values[:3])
                prompt_parts.append(f"Основные принципы: {values_text}.")
            
            # Use Russian LLM instructions
            ru_llm_instructions = ru_data.get("llm_instructions", "")
            if ru_llm_instructions:
                prompt_parts.append(ru_llm_instructions)
        else:
            # Use English core identity for English or unsupported languages
            prompt_parts.append(f"You are {self.name}, {self.personality.summary}.")
            
            # Personality traits
            if self.personality.personality:
                traits_text = ", ".join(self.personality.personality[:3])
                prompt_parts.append(f"Key traits: {traits_text}.")
            
            # Core values (condensed)
            if self.core_values:
                values_text = ", ".join(self.core_values[:3])
                prompt_parts.append(f"Core principles: {values_text}.")
            
            # Add LLM instructions
            if self.llm_instructions:
                prompt_parts.append(self.llm_instructions)
        
        return " ".join(prompt_parts)
    
    def get_external_system_prompt(self, language: Optional[str] = None) -> str:
        """Get system prompt for external LLMs - always English-based for consistency."""
        # External LLMs get English-only system prompts for maximum effectiveness
        prompt_parts = []
        
        prompt_parts.append(f"You are {self.name}, {self.personality.summary}.")
        
        # Key traits
        if self.personality.personality:
            traits_text = ", ".join(self.personality.personality[:2])
            prompt_parts.append(f"Key traits: {traits_text}.")
        
        # Instructions adapted for external use
        prompt_parts.append("Respond helpfully and concisely. Maintain your personality while adapting to the user's language preference.")
        
        return " ".join(prompt_parts)
    
    def get_user_facing_text(self, key: str, language: Optional[str] = None, **kwargs) -> str:
        """Get user-facing text with translation support."""
        target_language = language or self.primary_language
        
        # If requesting primary language or no translation available, use core
        if target_language == self.primary_language or target_language not in self.translations:
            return self._get_core_text(key, **kwargs)
        
        # Use translation
        translation_data = self.translations.get(target_language, {})
        
        if key == "summary":
            return translation_data.get("identity", {}).get("summary", self.personality.summary)
        elif key == "personality":
            return translation_data.get("identity", {}).get("personality", self.personality.personality)
        elif key == "core_values":
            return translation_data.get("core_values", self.core_values)
        elif key == "goals":
            return translation_data.get("goals", self.goals)
        elif key == "greeting":
            templates = translation_data.get("greeting_templates", {})
            template = templates.get("introduction", "Hello! I'm {name}, {summary}. How can I help?")
            return template.format(name=self.name, summary=self.get_user_facing_text("summary", language))
        
        return self._get_core_text(key, **kwargs)
    
    def _get_core_text(self, key: str, **kwargs) -> str:
        """Get core (English) text for a given key."""
        if key == "summary":
            return self.personality.summary
        elif key == "personality":
            return self.personality.personality
        elif key == "core_values":
            return self.core_values
        elif key == "goals":
            return self.goals
        elif key == "greeting":
            return f"Hello! I'm {self.name}, {self.personality.summary}. How can I help?"
        
        return ""
    
    def get_fallback_response(self, language: Optional[str] = None) -> str:
        """Get fallback response in appropriate language."""
        target_language = language or self.primary_language
        
        if target_language == "ru":
            summary = self.get_user_facing_text("summary", "ru")
            return f"Привет! Я {self.name}, {summary.lower()}. Чем могу помочь?"
        else:
            return f"Hello! I'm {self.name}, {self.personality.summary.lower()}. How can I help you?"
    
    def get_routing_threshold(self) -> int:
        """Get token threshold for routing decisions."""
        return self.operational_guidelines.routing_policy.max_tokens_local
    
    def should_require_deep_reasoning(self) -> bool:
        """Check if deep reasoning should be required for external routing."""
        return self.operational_guidelines.routing_policy.requires_deep_reasoning
    
    def get_model_path(self) -> str:
        """Get the configured model path."""
        return self.module_paths.local_model_gguf
    
    def get_memory_dir(self) -> str:
        """Get the configured memory directory."""
        return self.module_paths.memory_dir
    
    def reload(self) -> None:
        """Reload identity configuration from file."""
        self._load_identity()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert identity to dictionary for debugging/logging."""
        return {
            "name": self.name,
            "primary_language": self.primary_language,
            "supported_languages": self.supported_languages,
            "version": self.meta.version,
            "personality_summary": self.personality.summary,
            "routing_threshold": self.get_routing_threshold()
        }


# Global identity instance
identity = Identity()

# Export public interface
__all__ = [
    "Identity",
    "identity", 
    "validate_identity_file",
    "check_identity_completeness",
    "AGENT_TEMPLATES",
    "create_base_identity_template"
] 