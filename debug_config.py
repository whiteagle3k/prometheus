#!/usr/bin/env python3
"""Debug configuration loading."""

import os
from pathlib import Path
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

class TestSettings(BaseSettings):
    """Test settings class."""
    
    deep_reasoning_keywords_str: str = Field(
        default="analysis,strategy,complex,detailed,research,comprehensive,подробно,детально,анализ,стратегия,комплексный,исследование,quantum,квантовый,квантовая,квантовое,physics,физика,физический,физическая,theory,теория,relativity,относительность,science,наука,научный,научная,mechanism,механизм,principle,принцип,fundamental,фундаментальный,фундаментальная",
        validation_alias="DEEP_REASONING_KEYWORDS",
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
    
    @computed_field
    @property
    def deep_reasoning_keywords(self) -> list[str]:
        """Convert comma-separated keywords string to list."""
        return [keyword.strip() for keyword in self.deep_reasoning_keywords_str.split(",") if keyword.strip()]

if __name__ == "__main__":
    print("=== Testing Configuration Loading ===")
    
    # Test 1: Direct instantiation
    print("\n1. Direct instantiation:")
    test_settings = TestSettings()
    print(f"   Raw string: {test_settings.deep_reasoning_keywords_str[:50]}...")
    print(f"   Keyword count: {len(test_settings.deep_reasoning_keywords)}")
    print(f"   Has quantum: {'quantum' in test_settings.deep_reasoning_keywords}")
    print(f"   Has квантовая: {'квантовая' in test_settings.deep_reasoning_keywords}")
    
    # Test 2: Check environment
    print("\n2. Environment check:")
    env_value = os.getenv("DEEP_REASONING_KEYWORDS")
    print(f"   DEEP_REASONING_KEYWORDS env var: {env_value}")
    
    # Test 3: Check .env file
    print("\n3. .env file check:")
    env_file = Path(".env")
    if env_file.exists():
        content = env_file.read_text()
        if "DEEP_REASONING_KEYWORDS" in content:
            print(f"   Found in .env: {content}")
        else:
            print("   Not found in .env")
    else:
        print("   No .env file found")
    
    # Test 4: Check what the actual class default is
    print("\n4. Class field inspection:")
    field_info = TestSettings.model_fields['deep_reasoning_keywords_str']
    print(f"   Default value: {field_info.default[:50]}...")
    print(f"   Validation alias: {field_info.validation_alias}") 