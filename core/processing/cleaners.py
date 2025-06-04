"""Response cleaner processors for removing artifacts and cleaning text."""

import re
from typing import Any

from .base import ProcessingResult, TextProcessor
from .config import get_processor_config


class ResponseCleaner(TextProcessor):
    """Cleans response artifacts and formatting issues from text."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize response cleaner."""
        if config is None:
            config = get_processor_config("response_cleaner").parameters
        super().__init__(config)

        self.artifact_patterns = self.config.get("artifact_patterns", [])
        self.whitespace_cleanup = self.config.get("whitespace_cleanup", True)
        self.max_consecutive_newlines = self.config.get("max_consecutive_newlines", 2)

    def clean(self, text: str) -> str:
        """Clean artifacts from response text."""
        if not text:
            return text

        cleaned = text.strip()

        # Remove artifact patterns
        for pattern in self.artifact_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.MULTILINE).strip()

        if self.whitespace_cleanup:
            cleaned = self._clean_whitespace(cleaned)

        return cleaned

    def _clean_whitespace(self, text: str) -> str:
        """Clean excessive whitespace from text."""
        # Limit consecutive newlines
        max_newlines = "\n" * self.max_consecutive_newlines
        text = re.sub(r"\n\s*\n\s*\n+", max_newlines, text)

        # Multiple spaces to single space
        text = re.sub(r" +", " ", text)

        return text.strip()

    def process(self, text: str, context: dict[str, Any] | None = None) -> ProcessingResult:
        """Process text and return cleaned result."""
        original_length = len(text)
        cleaned_text = self.clean(text)
        cleaned_length = len(cleaned_text)

        artifacts_removed = original_length - cleaned_length

        return ProcessingResult(
            success=True,
            data=cleaned_text,
            confidence=1.0,
            metadata={
                "original_length": original_length,
                "cleaned_length": cleaned_length,
                "artifacts_removed": artifacts_removed,
                "patterns_applied": len(self.artifact_patterns)
            }
        )


class ChainOfThoughtExtractor(TextProcessor):
    """Extracts Chain-of-Thought reasoning from LLM responses."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize CoT extractor."""
        if config is None:
            config = get_processor_config("cot_extractor").parameters
        super().__init__(config)

        self.thought_start_marker = self.config.get("thought_start_marker", "<BEGIN_THOUGHT>")
        self.thought_end_marker = self.config.get("thought_end_marker", "<END_THOUGHT>")
        self.clean_artifacts = self.config.get("clean_artifacts", True)

    def extract_cot_and_response(self, raw_response: str) -> tuple[str, str]:
        """Extract Chain-of-Thought reasoning and final response from LLM output."""
        cleaned_response = raw_response.strip()

        # Look for Chain-of-Thought markers
        cot_start = cleaned_response.find(self.thought_start_marker)
        cot_end = cleaned_response.find(self.thought_end_marker)

        if cot_start != -1 and cot_end != -1 and cot_end > cot_start:
            # Extract CoT reasoning
            cot_reasoning = cleaned_response[cot_start + len(self.thought_start_marker):cot_end].strip()

            # Extract response (everything after end marker)
            final_response = cleaned_response[cot_end + len(self.thought_end_marker):].strip()

        elif cot_start != -1:
            # Incomplete CoT (only start marker) - treat as artifact
            if cot_start == 0:
                # CoT marker at the beginning
                lines = cleaned_response.split("\n")
                if len(lines) > 1:
                    final_response = "\n".join(lines[1:]).strip()
                else:
                    # Single line starting with incomplete CoT
                    marker_end = cleaned_response.find(")")
                    if marker_end != -1:
                        final_response = cleaned_response[marker_end + 1:].strip()
                    else:
                        final_response = cleaned_response[len(self.thought_start_marker):].strip()
                cot_reasoning = ""
            else:
                # CoT marker in the middle
                final_response = cleaned_response[:cot_start].strip()
                cot_reasoning = ""
        else:
            # No CoT markers found
            cot_reasoning = ""
            final_response = cleaned_response

        # Clean the final response of artifacts if enabled
        if self.clean_artifacts:
            cleaner = ResponseCleaner()
            final_response = cleaner.clean(final_response)

        return cot_reasoning, final_response

    def process(self, text: str, context: dict[str, Any] | None = None) -> ProcessingResult:
        """Process text and return extracted CoT and response."""
        cot_reasoning, final_response = self.extract_cot_and_response(text)

        return ProcessingResult(
            success=True,
            data={
                "cot_reasoning": cot_reasoning,
                "final_response": final_response,
                "has_cot": bool(cot_reasoning.strip())
            },
            confidence=1.0,
            metadata={
                "original_length": len(text),
                "cot_length": len(cot_reasoning),
                "response_length": len(final_response)
            }
        )
