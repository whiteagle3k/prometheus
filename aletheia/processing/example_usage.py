"""Example usage of the new processing system to replace hardcoded logic."""

from .pipeline import create_llm_response_pipeline, PipelineBuilder
from .filters import ContaminationFilter, DuplicationFilter, LengthFilter
from .config import get_processor_config


def process_llm_response_old_way(response_text: str) -> str:
    """Example of OLD hardcoded approach (what we're replacing)."""
    # This is the type of hardcoded logic we had before:
    
    # Hardcoded contamination patterns
    contamination_patterns = [
        r"Written by Assistant:.*",
        r"CV Template.*",
        # ... 40+ more hardcoded patterns
    ]
    
    # Hardcoded cleanup logic
    import re
    for pattern in contamination_patterns:
        response_text = re.sub(pattern, "", response_text, flags=re.IGNORECASE)
    
    # Hardcoded line filtering
    lines = response_text.split('\n')
    clean_lines = []
    for line in lines:
        if any(marker in line.lower() for marker in [
            "cv template", "task:", "approach:", # ... more hardcoded markers
        ]):
            continue
        clean_lines.append(line)
    
    # More hardcoded cleanup...
    return ' '.join(clean_lines)


def process_llm_response_new_way(response_text: str) -> str:
    """Example of NEW configurable approach."""
    # Create pipeline with configurable processors
    pipeline = create_llm_response_pipeline()
    
    # Process through pipeline
    result = pipeline.process(response_text)
    
    return result["processed_text"]


def create_custom_pipeline_example():
    """Example of creating a custom processing pipeline."""
    return (PipelineBuilder()
            .name("custom_response_processor")
            .add_filter(ContaminationFilter())  # Configured via JSON
            .add_filter(DuplicationFilter())    # Configured via JSON
            .add_filter(LengthFilter())         # Configured via JSON
            .build())


def dynamic_configuration_example():
    """Example of how configuration can be changed without code changes."""
    
    # Configuration is loaded from JSON files:
    config = get_processor_config("contamination_filter")
    
    # Can be modified at runtime:
    config.parameters["early_stops"].append("new_contamination_pattern")
    
    # Or disabled entirely:
    config.enabled = False
    
    # Processors automatically pick up the changes


# Benefits of the new approach:
"""
1. CONFIGURABLE: Patterns stored in JSON, not hardcoded in Python
2. MODULAR: Each processor has single responsibility
3. REUSABLE: Same processors can be used in different pipelines
4. TESTABLE: Each processor can be unit tested independently
5. MAINTAINABLE: Add new processors without touching existing code
6. DEBUGGABLE: Can see exactly which processor caused what change
7. EXTENSIBLE: Easy to add new processor types (ML-based, etc.)
8. RUNTIME-CONFIGURABLE: Change behavior without redeploying code
""" 