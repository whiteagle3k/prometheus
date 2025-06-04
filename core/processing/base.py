"""Base classes for text processing components."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ProcessorType(Enum):
    """Types of processors."""
    FILTER = "filter"
    EXTRACTOR = "extractor"
    VALIDATOR = "validator"
    DETECTOR = "detector"


@dataclass
class ProcessingResult:
    """Result from a text processor."""
    success: bool
    data: Any = None
    confidence: float = 1.0
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TextProcessor(ABC):
    """Base class for all text processors."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize processor with configuration."""
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.name = self.__class__.__name__

    @abstractmethod
    def process(self, text: str, context: dict[str, Any] | None = None) -> ProcessingResult:
        """Process text and return result."""

    def is_applicable(self, text: str, context: dict[str, Any] | None = None) -> bool:
        """Check if this processor should be applied to the text."""
        return self.enabled


class FilterProcessor(TextProcessor):
    """Base class for text filters (cleanup, sanitization)."""

    @abstractmethod
    def filter(self, text: str, context: dict[str, Any] | None = None) -> str:
        """Filter text and return cleaned version."""

    def process(self, text: str, context: dict[str, Any] | None = None) -> ProcessingResult:
        """Process by filtering text."""
        try:
            filtered_text = self.filter(text, context)
            return ProcessingResult(
                success=True,
                data=filtered_text,
                metadata={"original_length": len(text), "filtered_length": len(filtered_text)}
            )
        except Exception as e:
            return ProcessingResult(success=False, metadata={"error": str(e)})


class ExtractorProcessor(TextProcessor):
    """Base class for extracting information from text."""

    @abstractmethod
    def extract(self, text: str, context: dict[str, Any] | None = None) -> list[Any]:
        """Extract entities/information from text."""

    def process(self, text: str, context: dict[str, Any] | None = None) -> ProcessingResult:
        """Process by extracting information."""
        try:
            extracted = self.extract(text, context)
            return ProcessingResult(
                success=True,
                data=extracted,
                metadata={"count": len(extracted)}
            )
        except Exception as e:
            return ProcessingResult(success=False, metadata={"error": str(e)})


class DetectorProcessor(TextProcessor):
    """Base class for detecting patterns/conditions in text."""

    @abstractmethod
    def detect(self, text: str, context: dict[str, Any] | None = None) -> bool:
        """Detect if pattern/condition exists in text."""

    def process(self, text: str, context: dict[str, Any] | None = None) -> ProcessingResult:
        """Process by detecting patterns."""
        try:
            detected = self.detect(text, context)
            return ProcessingResult(
                success=True,
                data=detected,
                confidence=1.0 if detected else 0.0
            )
        except Exception as e:
            return ProcessingResult(success=False, metadata={"error": str(e)})


class ValidatorProcessor(TextProcessor):
    """Base class for validating text content."""

    @abstractmethod
    def validate(self, text: str, context: dict[str, Any] | None = None) -> list[str]:
        """Validate text and return list of issues found."""

    def process(self, text: str, context: dict[str, Any] | None = None) -> ProcessingResult:
        """Process by validating text."""
        try:
            issues = self.validate(text, context)
            return ProcessingResult(
                success=len(issues) == 0,
                data=issues,
                confidence=1.0 - (len(issues) * 0.2),  # Reduce confidence per issue
                metadata={"issue_count": len(issues)}
            )
        except Exception as e:
            return ProcessingResult(success=False, metadata={"error": str(e)})
