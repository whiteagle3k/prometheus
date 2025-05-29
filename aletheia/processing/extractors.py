"""Text extractor processors for extracting information from text."""

import re
from typing import Any, Dict, List, Optional
from .base import ExtractorProcessor
from .config import get_processor_config


class EntityExtractor(ExtractorProcessor):
    """Extracts entities and topics from text based on configuration."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize entity extractor."""
        if config is None:
            config = get_processor_config("entity_extractor").parameters
        super().__init__(config)
        
        self.scientific_terms = set(self.config.get("scientific_terms", []))
        self.compound_terms = self.config.get("compound_terms", [])
        self.min_word_length = self.config.get("min_word_length", 3)
        self.max_entities = self.config.get("max_entities", 5)
        self.exclude_words = set(self.config.get("exclude_words", []))
    
    def extract(self, text: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Extract entities from text."""
        if not text:
            return []
        
        entities = []
        text_lower = text.lower()
        
        # Extract compound terms first (these have priority)
        for compound_term in self.compound_terms:
            if compound_term.lower() in text_lower:
                entities.append(compound_term)
                # Remove this compound term from text to avoid double-extraction
                text_lower = text_lower.replace(compound_term.lower(), " ")
        
        # Extract individual words
        words_4plus = re.findall(r'\b\w{4,}\b', text_lower)
        words_3plus = re.findall(r'\b\w{3,}\b', text_lower)
        
        # Prioritize scientific terms
        for word in words_4plus + words_3plus:
            if len(entities) >= self.max_entities:
                break
                
            if (word in self.scientific_terms or 
                (len(word) >= self.min_word_length and word not in self.exclude_words)):
                
                # Don't add if already captured in compound term
                already_captured = any(word in entity.lower() for entity in entities)
                if not already_captured and word not in entities:
                    entities.append(word)
        
        return entities[:self.max_entities]


class NameExtractor(ExtractorProcessor):
    """Extracts user names from text based on configuration."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize name extractor."""
        if config is None:
            config = get_processor_config("name_extractor").parameters
        super().__init__(config)
        
        self.name_patterns = self.config.get("name_patterns", [])
        self.exclude_words = set(self.config.get("exclude_words", []))
        self.min_name_length = self.config.get("min_name_length", 2)
    
    def extract(self, text: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Extract names from text."""
        if not text:
            return []
        
        names = []
        text_lower = text.lower()
        
        for pattern in self.name_patterns:
            try:
                matches = re.finditer(pattern, text_lower)
                for match in matches:
                    if match.groups():
                        extracted_name = match.group(1).strip().capitalize()
                        
                        # Validate the extracted name
                        if (len(extracted_name) >= self.min_name_length and 
                            extracted_name.lower() not in self.exclude_words and
                            extracted_name not in names):
                            names.append(extracted_name)
            except re.error as e:
                print(f"Invalid name pattern '{pattern}': {e}")
                continue
        
        return names


class TopicExtractor(ExtractorProcessor):
    """Extracts conversation topics from text."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize topic extractor."""
        if config is None:
            config = get_processor_config("topic_extractor").parameters
        super().__init__(config)
        
        self.topic_categories = self.config.get("topic_categories", {})
        self.priority_words = set(self.config.get("priority_words", []))
        self.exclude_temporal = set(self.config.get("exclude_temporal", []))
    
    def extract(self, text: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Extract topics from text."""
        if not text:
            return []
        
        # Use EntityExtractor to get potential topics
        entity_extractor = EntityExtractor()
        entities = entity_extractor.extract(text, context)
        
        topics = []
        text_lower = text.lower()
        
        # Categorize and prioritize topics
        for entity in entities:
            entity_lower = entity.lower()
            
            # Skip temporal words
            if entity_lower in self.exclude_temporal:
                continue
            
            # Check if it's a priority topic
            if entity_lower in self.priority_words:
                topics.insert(0, entity)  # Add to front
            else:
                # Check topic categories
                for category, category_words in self.topic_categories.items():
                    if entity_lower in category_words:
                        topics.append(entity)
                        break
                else:
                    # Generic topic if not in any category
                    topics.append(entity)
        
        return topics[:3]  # Return top 3 topics 