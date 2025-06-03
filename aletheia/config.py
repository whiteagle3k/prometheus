"""Configuration management for Aletheia."""

import os
from pathlib import Path
from typing import Optional

# Set tokenizer parallelism to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Main configuration class for Aletheia."""

    # External LLM API Keys
    anthropic_api_key: Optional[str] = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, validation_alias="OPENAI_API_KEY")

    # Local Model Configuration (can be overridden by identity.json)
    local_model_path: Path = Field(
        default=Path("./models/phi-3-mini-3.8b-q4_k.gguf"),
        validation_alias="LOCAL_MODEL_PATH",
    )
    # Utility Model Configuration (NEW: small fast model for utility tasks)
    utility_model_path: Path = Field(
        default=Path("./models/phi-3-mini-3.8b-q4_k.gguf"),
        validation_alias="UTILITY_MODEL_PATH",
    )
    local_model_context_size: int = Field(default=8192, validation_alias="LOCAL_MODEL_CONTEXT_SIZE")
    local_model_gpu_layers: int = Field(default=32, validation_alias="LOCAL_MODEL_GPU_LAYERS")

    # Hardware-specific settings
    use_metal: bool = Field(default=True)  # macOS Metal acceleration
    use_cuda: bool = Field(default=False)  # NVIDIA CUDA (for future RTX migration)

    # Vector Database (can be overridden by identity.json)
    chroma_persist_dir: Path = Field(
        default=Path("./data/chroma_db"), validation_alias="CHROMA_PERSIST_DIR"
    )

    # Agent Configuration
    max_memory_entries: int = Field(default=1000, validation_alias="MAX_MEMORY_ENTRIES")
    memory_summarization_threshold: int = Field(
        default=500, validation_alias="MEMORY_SUMMARIZATION_THRESHOLD"
    )
    reflection_enabled: bool = Field(default=True, validation_alias="REFLECTION_ENABLED")

    # Hierarchical Memory Configuration
    use_hierarchical_memory: bool = Field(default=True, validation_alias="USE_HIERARCHICAL_MEMORY")
    raw_memory_limit: int = Field(default=200, validation_alias="RAW_MEMORY_LIMIT")
    summary_memory_limit: int = Field(default=100, validation_alias="SUMMARY_MEMORY_LIMIT")
    key_facts_limit: int = Field(default=50, validation_alias="KEY_FACTS_LIMIT")
    memory_archive_days: int = Field(default=30, validation_alias="MEMORY_ARCHIVE_DAYS")
    memory_compression_days: int = Field(default=7, validation_alias="MEMORY_COMPRESSION_DAYS")
    memory_key_facts_days: int = Field(default=14, validation_alias="MEMORY_KEY_FACTS_DAYS")

    # Routing Configuration (can be overridden by identity.json)
    local_token_threshold: int = Field(default=1024, validation_alias="LOCAL_TOKEN_THRESHOLD")
    # Handle deep reasoning keywords as a string first, then convert to list
    deep_reasoning_keywords_str: str = Field(
        default="analysis,strategy,complex,detailed,research,comprehensive,подробно,детально,анализ,стратегия,комплексный,исследование,quantum,квантовый,квантовая,квантовое,physics,физика,физический,физическая,theory,теория,relativity,относительность,science,наука,научный,научная,mechanism,механизм,principle,принцип,fundamental,фундаментальный,фундаментальная",
        validation_alias="DEEP_REASONING_KEYWORDS",
    )

    # Identity configuration path
    identity_path: Path = Field(
        default=Path("./aletheia/identity/identity.json"),
        validation_alias="IDENTITY_PATH"
    )

    # Logging
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    
    # Development/Production mode
    development_mode: bool = Field(default=True, validation_alias="DEVELOPMENT_MODE")
    allow_complete_memory_reset: bool = Field(default=True, validation_alias="ALLOW_COMPLETE_MEMORY_RESET")

    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @computed_field
    @property
    def deep_reasoning_keywords(self) -> list[str]:
        """Convert comma-separated keywords string to list."""
        return [keyword.strip() for keyword in self.deep_reasoning_keywords_str.split(",") if keyword.strip()]

    def _init_paths_and_hardware(self) -> None:
        """Post-initialization setup."""
        # Create necessary directories
        self.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
        self.local_model_path.parent.mkdir(parents=True, exist_ok=True)

        # Hardware detection and optimization
        if os.uname().sysname == "Darwin":
            self.use_metal = True
            self.use_cuda = False
        elif os.name == "nt" or "linux" in os.uname().sysname.lower():
            # Future RTX 4070 migration path
            self.use_metal = False
            # CUDA detection would go here

    def update_from_identity(self, identity_instance) -> None:
        """Update configuration from identity settings."""
        try:
            # Update model path if specified in identity
            if identity_instance.module_paths.local_model_gguf:
                identity_model_path = Path(identity_instance.module_paths.local_model_gguf)
                if identity_model_path.exists():
                    self.local_model_path = identity_model_path
                    print(f"📁 Using model path from identity: {identity_model_path}")

            # Update utility model path if specified in identity
            if hasattr(identity_instance.module_paths, 'utility_model_gguf') and identity_instance.module_paths.utility_model_gguf:
                identity_utility_path = Path(identity_instance.module_paths.utility_model_gguf)
                if identity_utility_path.exists():
                    self.utility_model_path = identity_utility_path
                    print(f"⚡ Using utility model path from identity: {identity_utility_path}")
                else:
                    print(f"⚠️  Utility model specified in identity not found: {identity_utility_path}")
                    # Fall back to main model if specified utility model doesn't exist
                    if hasattr(self, 'local_model_path'):
                        self.utility_model_path = self.local_model_path
                        print(f"⚡ Falling back to main model as utility model: {self.local_model_path}")
            else:
                # No utility model specified in identity - this is fine, keep default or use main model
                print(f"💡 No utility model specified in identity, using default: {self.utility_model_path}")
                # Only fall back to main model if the default doesn't exist
                if not self.utility_model_path.exists() and hasattr(self, 'local_model_path'):
                    self.utility_model_path = self.local_model_path
                    print(f"⚡ Default utility model not found, using main model: {self.local_model_path}")

            # Update memory directory if specified in identity
            if identity_instance.module_paths.memory_dir:
                identity_memory_dir = Path(identity_instance.module_paths.memory_dir)
                # Update chroma directory to use identity's memory dir
                self.chroma_persist_dir = identity_memory_dir / "chroma_db"
                self.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
                print(f"💾 Using memory directory from identity: {identity_memory_dir}")

            # Update routing threshold from identity
            identity_threshold = identity_instance.get_routing_threshold()
            if identity_threshold and identity_threshold != self.local_token_threshold:
                self.local_token_threshold = identity_threshold
                print(f"🎯 Using routing threshold from identity: {identity_threshold}")

        except Exception as e:
            print(f"⚠️  Warning: Could not update config from identity: {e}")


# Global config instance
config = AppSettings()
config._init_paths_and_hardware()

# Load identity and update config accordingly
try:
    from .identity import identity
    config.update_from_identity(identity)
    print(f"✅ Identity loaded: {identity.name} v{identity.meta.version}")
except Exception as e:
    print(f"⚠️  Warning: Could not load identity configuration: {e}")
