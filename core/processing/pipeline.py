"""Processing pipeline for chaining text processors."""

from typing import Any

from .base import ProcessingResult, TextProcessor


class ProcessingPipeline:
    """Pipeline for chaining text processors."""

    def __init__(self, name: str = "default"):
        """Initialize pipeline."""
        self.name = name
        self.processors: list[TextProcessor] = []
        self.results_cache: dict[str, list[ProcessingResult]] = {}

    def add_processor(self, processor: TextProcessor) -> "ProcessingPipeline":
        """Add a processor to the pipeline."""
        self.processors.append(processor)
        return self

    def remove_processor(self, processor_name: str) -> "ProcessingPipeline":
        """Remove a processor by name."""
        self.processors = [p for p in self.processors if p.name != processor_name]
        return self

    def process(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Process text through the entire pipeline."""
        context = context or {}
        results = []
        current_text = text

        for processor in self.processors:
            if not processor.is_applicable(current_text, context):
                continue

            result = processor.process(current_text, context)
            results.append({
                "processor": processor.name,
                "type": type(processor).__name__,
                "result": result
            })

            # If this is a filter processor, update the text for next processor
            if hasattr(processor, "filter") and result.success:
                current_text = result.data

            # Add processor result to context for next processors
            context[f"{processor.name}_result"] = result

        return {
            "original_text": text,
            "processed_text": current_text,
            "results": results,
            "success": all(r["result"].success for r in results),
            "pipeline_name": self.name
        }

    def get_processors_by_type(self, processor_type: type[TextProcessor]) -> list[TextProcessor]:
        """Get all processors of a specific type."""
        return [p for p in self.processors if isinstance(p, processor_type)]

    def clear(self) -> "ProcessingPipeline":
        """Clear all processors from pipeline."""
        self.processors.clear()
        return self


class PipelineBuilder:
    """Builder for creating processing pipelines."""

    def __init__(self):
        """Initialize builder."""
        self.pipeline = ProcessingPipeline()

    def name(self, name: str) -> "PipelineBuilder":
        """Set pipeline name."""
        self.pipeline.name = name
        return self

    def add_filter(self, filter_processor: TextProcessor) -> "PipelineBuilder":
        """Add a filter processor."""
        self.pipeline.add_processor(filter_processor)
        return self

    def add_extractor(self, extractor_processor: TextProcessor) -> "PipelineBuilder":
        """Add an extractor processor."""
        self.pipeline.add_processor(extractor_processor)
        return self

    def add_detector(self, detector_processor: TextProcessor) -> "PipelineBuilder":
        """Add a detector processor."""
        self.pipeline.add_processor(detector_processor)
        return self

    def add_validator(self, validator_processor: TextProcessor) -> "PipelineBuilder":
        """Add a validator processor."""
        self.pipeline.add_processor(validator_processor)
        return self

    def build(self) -> ProcessingPipeline:
        """Build and return the pipeline."""
        return self.pipeline


# Convenience function for creating common pipelines
def create_llm_response_pipeline() -> ProcessingPipeline:
    """Create a pipeline for processing LLM responses."""
    from .filters import ContaminationFilter, DuplicationFilter
    from .validators import FactualValidator

    return (PipelineBuilder()
            .name("llm_response")
            .add_filter(ContaminationFilter())
            .add_filter(DuplicationFilter())
            .add_validator(FactualValidator())
            .build())


def create_context_analysis_pipeline() -> ProcessingPipeline:
    """Create a pipeline for analyzing conversation context."""
    from .detectors import LanguageDetector, ReferenceDetector
    from .extractors import EntityExtractor, NameExtractor

    return (PipelineBuilder()
            .name("context_analysis")
            .add_detector(LanguageDetector())
            .add_extractor(EntityExtractor())
            .add_extractor(NameExtractor())
            .add_detector(ReferenceDetector())
            .build())


def create_simple_response_pipeline() -> ProcessingPipeline:
    """Create a simple pipeline for basic response cleanup."""
    from .filters import ContaminationFilter, LengthFilter

    return (PipelineBuilder()
            .name("simple_response")
            .add_filter(ContaminationFilter())
            .add_filter(LengthFilter())
            .build())
