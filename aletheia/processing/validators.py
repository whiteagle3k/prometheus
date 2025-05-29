"""Text validator processors for validating content quality and accuracy."""

import re
from typing import Any, Dict, List, Optional
from .base import ValidatorProcessor
from .config import get_processor_config


class FactualValidator(ValidatorProcessor):
    """Validates factual accuracy of responses."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize factual validator."""
        if config is None:
            config = get_processor_config("factual_validator").parameters
        super().__init__(config)
        
        self.confusion_checks = self.config.get("confusion_checks", {})
        self.contradiction_pairs = self.config.get("contradiction_pairs", [])
        self.impossible_combinations = self.config.get("impossible_combinations", {})
    
    def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Validate factual accuracy and return list of issues."""
        if not text:
            return []
        
        issues = []
        text_lower = text.lower()
        user_input = context.get("user_input", "").lower() if context else ""
        
        # Check for specific confusions (e.g., water vapor vs hydrogen)
        for confusion_name, confusion_config in self.confusion_checks.items():
            question_terms = confusion_config.get("question_terms", [])
            error_terms = confusion_config.get("error_terms", [])
            
            if user_input and any(term in user_input for term in question_terms):
                if any(error in text_lower for error in error_terms):
                    issues.append(f"confusion_{confusion_name}")
        
        # Check for contradictory statements
        for positive_terms, negative_terms in self.contradiction_pairs:
            has_positive = any(term in text_lower for term in positive_terms)
            has_negative = any(term in text_lower for term in negative_terms)
            if has_positive and has_negative:
                issues.append("contradictory_statements")
        
        # Check for impossible combinations
        for domain, combinations in self.impossible_combinations.items():
            if user_input and any(term in user_input for term in [domain]):
                for combo in combinations:
                    if all(term in text_lower for term in combo):
                        issues.append(f"impossible_{domain}_combination")
        
        return issues


class ContentValidator(ValidatorProcessor):
    """Validates content quality and completeness."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize content validator."""
        if config is None:
            config = get_processor_config("content_validator").parameters
        super().__init__(config)
        
        self.vague_indicators = self.config.get("vague_indicators", [])
        self.vague_threshold = self.config.get("vague_threshold", 3)
        self.definition_requirements = self.config.get("definition_requirements", {})
        self.min_length = self.config.get("min_length", 20)
        self.required_elements = self.config.get("required_elements", {})
    
    def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Validate content quality and return list of issues."""
        if not text:
            return ["empty_response"]
        
        issues = []
        text_lower = text.lower()
        user_input = context.get("user_input", "").lower() if context else ""
        
        # Check for overly vague responses
        vague_count = sum(1 for indicator in self.vague_indicators if indicator in text_lower)
        if vague_count > self.vague_threshold:
            issues.append("overly_vague_response")
        
        # Check minimum length
        if len(text) < self.min_length:
            issues.append("response_too_short")
        
        # Check definition requirements
        def_config = self.definition_requirements
        question_patterns = def_config.get("question_patterns", [])
        required_words = def_config.get("required_words", [])
        
        if user_input and any(pattern in user_input for pattern in question_patterns):
            if not any(word in text_lower for word in required_words):
                issues.append("no_definition_provided")
        
        # Check for required elements based on question type
        for question_type, required in self.required_elements.items():
            if user_input and any(keyword in user_input for keyword in required.get("triggers", [])):
                missing_elements = [elem for elem in required.get("elements", []) 
                                  if elem not in text_lower]
                if missing_elements:
                    issues.append(f"missing_{question_type}_elements")
        
        return issues


class StructureValidator(ValidatorProcessor):
    """Validates response structure and format."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize structure validator."""
        if config is None:
            config = get_processor_config("structure_validator").parameters
        super().__init__(config)
        
        self.required_format = self.config.get("required_format", {})
        self.forbidden_patterns = self.config.get("forbidden_patterns", [])
        self.repetition_threshold = self.config.get("repetition_threshold", 3)
    
    def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Validate response structure and return list of issues."""
        if not text:
            return []
        
        issues = []
        
        # Check for forbidden patterns (training artifacts, etc.)
        for pattern in self.forbidden_patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    issues.append("contains_forbidden_pattern")
                    break
            except re.error:
                continue
        
        # Check for excessive repetition
        words = text.lower().split()
        word_counts = {}
        for word in words:
            if len(word) > 3:  # Only check longer words
                word_counts[word] = word_counts.get(word, 0) + 1
        
        for word, count in word_counts.items():
            if count > self.repetition_threshold:
                issues.append("excessive_repetition")
                break
        
        # Check required format if specified
        if context and "format_type" in context:
            format_type = context["format_type"]
            if format_type in self.required_format:
                format_rules = self.required_format[format_type]
                
                # Check required fields
                for field in format_rules.get("required_fields", []):
                    if field not in text:
                        issues.append(f"missing_required_field_{field}")
        
        return issues


class ConsistencyValidator(ValidatorProcessor):
    """Validates consistency with conversation context."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize consistency validator."""
        if config is None:
            config = get_processor_config("consistency_validator").parameters
        super().__init__(config)
        
        self.context_requirements = self.config.get("context_requirements", {})
        self.topic_consistency_check = self.config.get("topic_consistency_check", True)
    
    def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Validate consistency with context and return list of issues."""
        if not text or not context:
            return []
        
        issues = []
        text_lower = text.lower()
        
        # Check if response addresses the current topic
        if self.topic_consistency_check and "current_topic" in context:
            current_topic = context["current_topic"]
            if current_topic and current_topic.lower() not in text_lower:
                # Check if this is a reference question that should mention the topic
                if context.get("is_reference_question", False):
                    issues.append("topic_not_addressed")
        
        # Check context requirements
        for requirement_type, requirement_config in self.context_requirements.items():
            triggers = requirement_config.get("triggers", [])
            required_mentions = requirement_config.get("required_mentions", [])
            
            user_input = context.get("user_input", "").lower()
            if any(trigger in user_input for trigger in triggers):
                if not any(mention in text_lower for mention in required_mentions):
                    issues.append(f"missing_{requirement_type}_context")
        
        return issues 