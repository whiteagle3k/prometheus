"""Text filter processors for cleaning and sanitizing text."""

import re
from typing import Any, Dict, List, Optional
from .base import FilterProcessor, ProcessingResult
from .config import get_processor_config


class ContaminationFilter(FilterProcessor):
    """Removes contamination patterns from text based on configuration."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize contamination filter."""
        if config is None:
            config = get_processor_config("contamination_filter").parameters
        super().__init__(config)
        
        # Load patterns from config instead of hardcoding
        self.regex_patterns = self.config.get("regex_patterns", [])
        self.keyword_markers = self.config.get("keyword_markers", [])
        self.stop_phrases = self.config.get("stop_phrases", [])
        self.early_stops = self.config.get("early_stops", [])
    
    def filter(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Filter contamination from text."""
        if not text:
            return text
        
        response = text.strip()
        
        # Apply regex pattern cleanup
        for pattern in self.regex_patterns:
            try:
                response = re.sub(pattern, "", response, flags=re.IGNORECASE | re.DOTALL)
            except re.error as e:
                print(f"Invalid regex pattern '{pattern}': {e}")
                continue
        
        # Filter by line markers
        if self.keyword_markers:
            response = self._filter_by_line_markers(response)
        
        # Apply stop phrase cleanup
        for stop_phrase in self.stop_phrases:
            if stop_phrase in response:
                response = response.split(stop_phrase)[0].strip()
                break
        
        # Early contamination stopping
        for stop in self.early_stops:
            if stop.lower() in response.lower():
                response = response.split(stop)[0].strip()
                break
        
        # Clean up whitespace
        response = re.sub(r'\s+', ' ', response).strip()
        
        return response
    
    def _filter_by_line_markers(self, text: str) -> str:
        """Filter lines containing contamination markers."""
        lines = text.split('\n')
        clean_lines = []
        
        for line in lines:
            line = line.strip()
            if len(line) < 3:  # Skip very short lines
                continue
            
            # Check if line contains any contamination markers
            line_lower = line.lower()
            has_contamination = any(marker in line_lower for marker in self.keyword_markers)
            
            if not has_contamination:
                clean_lines.append(line)
        
        return ' '.join(clean_lines) if clean_lines else text


class DuplicationFilter(FilterProcessor):
    """Removes duplicate sentences and phrases from text."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize duplication filter."""
        if config is None:
            config = get_processor_config("duplication_filter").parameters
        super().__init__(config)
        
        self.similarity_threshold = self.config.get("similarity_threshold", 0.7)
        self.min_sentence_length = self.config.get("min_sentence_length", 10)
    
    def filter(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Remove duplicate sentences from text."""
        if not text:
            return text
        
        sentences = text.split('. ')
        clean_sentences = []
        seen_sentences = set()
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < self.min_sentence_length:
                continue
            
            # Normalize for comparison
            normalized = re.sub(r'[^\w\s]', '', sentence.lower()).strip()
            
            # Check similarity with existing sentences
            is_duplicate = False
            for seen in seen_sentences:
                if self._calculate_similarity(normalized, seen) > self.similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                clean_sentences.append(sentence)
                seen_sentences.add(normalized)
        
        if clean_sentences:
            result = '. '.join(clean_sentences)
            if result and not result.endswith(('.', '!', '?')):
                result += '.'
            return result
        
        return text
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0


class LengthFilter(FilterProcessor):
    """Filters text based on length requirements."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize length filter."""
        if config is None:
            config = get_processor_config("length_filter").parameters
        super().__init__(config)
        
        self.min_length = self.config.get("min_length", 20)
        self.max_length = self.config.get("max_length", 5000)
        self.fallback_text = self.config.get("fallback_text", "")
    
    def filter(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Filter text based on length."""
        if not text:
            return self.fallback_text
        
        text_length = len(text)
        
        # Check minimum length
        if text_length < self.min_length:
            if self.fallback_text:
                return self.fallback_text
            return text
        
        # Check maximum length (truncate if needed)
        if text_length > self.max_length:
            return text[:self.max_length].rsplit(' ', 1)[0] + "..."
        
        return text


class LanguageFilter(FilterProcessor):
    """Filters text based on language detection."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize language filter."""
        if config is None:
            config = get_processor_config("language_filter").parameters
        super().__init__(config)
        
        self.allowed_languages = self.config.get("allowed_languages", ["en", "ru"])
        self.cyrillic_threshold = self.config.get("cyrillic_threshold", 0.3)
    
    def filter(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Filter text based on detected language."""
        if not text:
            return text
        
        detected_language = self._detect_language(text)
        
        if detected_language in self.allowed_languages:
            return text
        
        # If language not allowed, return empty or fallback
        return self.config.get("fallback_text", "")
    
    def _detect_language(self, text: str) -> str:
        """Detect language of text."""
        cyrillic_chars = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
        total_chars = len([char for char in text if char.isalpha()])
        
        if total_chars > 0 and cyrillic_chars / total_chars > self.cyrillic_threshold:
            return "ru"
        return "en" 