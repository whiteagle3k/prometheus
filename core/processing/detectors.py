"""Text detector processors for detecting patterns and conditions in text."""

import re
from typing import Any, Dict, List, Optional
from .base import DetectorProcessor, ProcessingResult
from .config import get_processor_config


class LanguageDetector(DetectorProcessor):
    """Detects the language of text."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize language detector."""
        if config is None:
            config = get_processor_config("language_detector").parameters
        super().__init__(config)
        
        self.cyrillic_threshold = self.config.get("cyrillic_threshold", 0.3)
        self.supported_languages = self.config.get("supported_languages", ["en", "ru"])
    
    def detect(self, text: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Detect if text is in a supported language."""
        if not text:
            return False
        
        detected_language = self._detect_language(text)
        return detected_language in self.supported_languages
    
    def process(self, text: str, context: Optional[Dict[str, Any]] = None):
        """Override to return the detected language in data."""
        detected_language = self._detect_language(text)
        return ProcessingResult(
            success=True,
            data=detected_language,
            confidence=1.0 if detected_language in self.supported_languages else 0.0,
            metadata={"supported_languages": self.supported_languages}
        )
    
    def _detect_language(self, text: str) -> str:
        """Detect language of text."""
        cyrillic_chars = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
        total_chars = len([char for char in text if char.isalpha()])
        
        if total_chars > 0 and cyrillic_chars / total_chars > self.cyrillic_threshold:
            return "ru"
        return "en"


class ReferenceDetector(DetectorProcessor):
    """Detects references to previous conversation."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize reference detector."""
        if config is None:
            config = get_processor_config("reference_detector").parameters
        super().__init__(config)
        
        self.pronouns = self.config.get("pronouns", [])
        self.continuation_phrases = self.config.get("continuation_phrases", [])
        self.implicit_patterns = self.config.get("implicit_patterns", [])
    
    def detect(self, text: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Detect if text contains references to previous conversation."""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Check for pronouns using word boundaries to avoid substring matches
        has_pronouns = any(re.search(rf'\b{re.escape(pronoun)}\b', text_lower) for pronoun in self.pronouns)
        
        # Check for continuation phrases
        has_continuation = any(phrase in text_lower for phrase in self.continuation_phrases)
        
        # Check for implicit continuation patterns
        has_implicit = any(re.search(pattern, text_lower) for pattern in self.implicit_patterns)
        
        return has_pronouns or has_continuation or has_implicit
    
    def process(self, text: str, context: Optional[Dict[str, Any]] = None):
        """Override to return detailed reference information."""
        text_lower = text.lower()
        
        # Check for pronouns using word boundaries
        has_pronouns = any(re.search(rf'\b{re.escape(pronoun)}\b', text_lower) for pronoun in self.pronouns)
        has_continuation = any(phrase in text_lower for phrase in self.continuation_phrases)
        has_implicit = any(re.search(pattern, text_lower) for pattern in self.implicit_patterns)
        
        detected = has_pronouns or has_continuation or has_implicit
        
        return ProcessingResult(
            success=True,
            data={
                "has_references": detected,
                "has_pronouns": has_pronouns,
                "has_continuation": has_continuation,
                "has_implicit": has_implicit
            },
            confidence=1.0 if detected else 0.0,
            metadata={
                "pronouns_found": [p for p in self.pronouns if re.search(rf'\b{re.escape(p)}\b', text_lower)] if has_pronouns else [],
                "continuation_found": [p for p in self.continuation_phrases if p in text_lower] if has_continuation else []
            }
        )


class SelfReferenceDetector(DetectorProcessor):
    """Detects if user is asking about themselves."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize self-reference detector."""
        if config is None:
            config = get_processor_config("self_reference_detector").parameters
        super().__init__(config)
        
        self.self_reference_patterns = self.config.get("self_reference_patterns", [])
    
    def detect(self, text: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Detect if text contains self-reference questions."""
        if not text:
            return False
        
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in self.self_reference_patterns)


class GreetingDetector(DetectorProcessor):
    """Detects simple greetings and casual conversation."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize greeting detector."""
        if config is None:
            config = get_processor_config("greeting_detector").parameters
        super().__init__(config)
        
        self.greeting_patterns = self.config.get("greeting_patterns", [])
        self.casual_patterns = self.config.get("casual_patterns", [])
    
    def detect(self, text: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Detect if text is a greeting or casual conversation."""
        if not text:
            return False
        
        text_lower = text.lower()
        
        is_greeting = any(pattern in text_lower for pattern in self.greeting_patterns)
        is_casual = any(pattern in text_lower for pattern in self.casual_patterns)
        
        return is_greeting or is_casual


class ComplexityDetector(DetectorProcessor):
    """Detects if a task requires complex planning."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize complexity detector."""
        if config is None:
            config = get_processor_config("complexity_detector").parameters
        super().__init__(config)
        
        self.planning_indicators = self.config.get("planning_indicators", [])
        self.sequential_markers = self.config.get("sequential_markers", [])
        self.length_threshold = self.config.get("length_threshold", 50)
        self.question_threshold = self.config.get("question_threshold", 3)
    
    def detect(self, text: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Detect if text represents a complex task."""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Check for explicit planning indicators
        has_planning_keywords = any(indicator in text_lower for indicator in self.planning_indicators)
        
        # Check for sequential tasks
        has_sequential = any(marker in text_lower for marker in self.sequential_markers)
        
        # Check length complexity
        is_long = len(text.split()) > self.length_threshold
        
        # Check multiple questions
        has_multiple_questions = text.count('?') >= self.question_threshold and len(text.split()) > 20
        
        return has_planning_keywords or has_sequential or (is_long and has_multiple_questions)


class TechnicalDetector(DetectorProcessor):
    """Detects if content requires technical/scientific knowledge."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize technical detector."""
        if config is None:
            config = get_processor_config("technical_detector").parameters
        super().__init__(config)
        
        self.technical_domains = self.config.get("technical_domains", {})
        self.question_patterns = self.config.get("question_patterns", [])
    
    def detect(self, text: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Detect if text requires technical knowledge."""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Check for technical domain keywords
        for domain, keywords in self.technical_domains.items():
            if any(keyword in text_lower for keyword in keywords):
                return True
        
        # Check for technical question patterns
        return any(pattern in text_lower for pattern in self.question_patterns) 