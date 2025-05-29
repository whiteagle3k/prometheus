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

    # Local Model Configuration
    local_model_path: Path = Field(
        default=Path("./models/phi-3-mini-3.8b-q4_k.gguf"),
        validation_alias="LOCAL_MODEL_PATH",
    )
    local_model_context_size: int = Field(default=4096, validation_alias="LOCAL_MODEL_CONTEXT_SIZE")
    local_model_gpu_layers: int = Field(default=32, validation_alias="LOCAL_MODEL_GPU_LAYERS")

    # Hardware-specific settings
    use_metal: bool = Field(default=True)  # macOS Metal acceleration
    use_cuda: bool = Field(default=False)  # NVIDIA CUDA (for future RTX migration)

    # Vector Database
    chroma_persist_dir: Path = Field(
        default=Path("./data/chroma_db"), validation_alias="CHROMA_PERSIST_DIR"
    )

    # Agent Configuration
    max_memory_entries: int = Field(default=1000, validation_alias="MAX_MEMORY_ENTRIES")
    memory_summarization_threshold: int = Field(
        default=500, validation_alias="MEMORY_SUMMARIZATION_THRESHOLD"
    )
    reflection_enabled: bool = Field(default=True, validation_alias="REFLECTION_ENABLED")

    # Routing Configuration
    local_token_threshold: int = Field(default=1024, validation_alias="LOCAL_TOKEN_THRESHOLD")
    # Handle deep reasoning keywords as a string first, then convert to list
    deep_reasoning_keywords_str: str = Field(
        default="analysis,strategy,complex,detailed,research,comprehensive",
        validation_alias="DEEP_REASONING_KEYWORDS",
    )

    # Logging
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

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


# Global config instance
config = AppSettings()
config._init_paths_and_hardware()
