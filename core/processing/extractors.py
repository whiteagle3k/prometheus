"""Text extractor processors for extracting information from text."""

import re
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

from .base import ExtractorProcessor
from .config import get_processor_config


@dataclass
class UserDataPoint:
    """Represents a piece of user-provided information."""
    key: str
    value: str
    category: str
    timestamp: datetime
    source_context: str
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "timestamp": self.timestamp.isoformat(),
            "source_context": self.source_context,
            "confidence": self.confidence
        }


class UserDataExtractor(ExtractorProcessor):
    """Extracts user-provided data and information from text."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize user data extractor."""
        if config is None:
            config = get_processor_config("user_data_extractor").parameters
        super().__init__(config)
        
        self.physical_patterns = self.config.get("physical_patterns", [])
        self.goal_patterns = self.config.get("goal_patterns", [])
        self.preference_patterns = self.config.get("preference_patterns", [])
        self.personal_patterns = self.config.get("personal_patterns", [])
        self.correction_patterns = self.config.get("correction_patterns", [])
        self.info_providing_indicators = self.config.get("information_providing_indicators", [])
        self.question_indicators = self.config.get("question_indicators", [])
        self.data_query_patterns = self.config.get("data_query_patterns", [])
    
    def extract(self, text: str, context: Optional[Dict[str, Any]] = None) -> List[UserDataPoint]:
        """Extract user data points from text."""
        if not text:
            return []
        
        data_points = []
        timestamp = datetime.now()
        context_str = context.get("source_context", text[:100]) if context else text[:100]
        
        print(f"  🔍 Analyzing input: '{text}'")
        
        # Extract physical data
        for pattern_config in self.physical_patterns:
            category = "physical"
            data_points.extend(self._extract_pattern_matches(
                text, pattern_config, category, timestamp, context_str
            ))
        
        # Extract goals
        for pattern_config in self.goal_patterns:
            category = "goals"
            data_points.extend(self._extract_pattern_matches(
                text, pattern_config, category, timestamp, context_str
            ))
        
        # Extract preferences
        for pattern_config in self.preference_patterns:
            category = "preferences"
            data_points.extend(self._extract_pattern_matches(
                text, pattern_config, category, timestamp, context_str
            ))
        
        # Extract personal info
        for pattern_config in self.personal_patterns:
            category = "personal"
            data_points.extend(self._extract_pattern_matches(
                text, pattern_config, category, timestamp, context_str
            ))
        
        # Extract corrections/feedback
        for pattern_config in self.correction_patterns:
            category = "feedback"
            data_points.extend(self._extract_pattern_matches(
                text, pattern_config, category, timestamp, context_str
            ))
        
        print(f"  📊 Total extracted: {len(data_points)} data points")
        
        return data_points
    
    def _extract_pattern_matches(
        self, 
        text: str, 
        pattern_config: Dict[str, Any], 
        category: str,
        timestamp: datetime, 
        context_str: str
    ) -> List[UserDataPoint]:
        """Extract matches for a specific pattern configuration."""
        matches = []
        
        try:
            pattern = pattern_config["pattern"]
            regex_matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in regex_matches:
                value = match.group(1).strip()
                
                print(f"  ✅ Pattern matched: {pattern_config['key']} = {value} (pattern: {pattern[:50]}...)")
                
                # Clean and normalize value
                value = self._normalize_value(value, pattern_config, match.group(0))
                
                data_point = UserDataPoint(
                    key=pattern_config["key"],
                    value=value,
                    category=category,
                    timestamp=timestamp,
                    source_context=context_str,
                    confidence=pattern_config["confidence"]
                )
                matches.append(data_point)
                
        except re.error as e:
            print(f"Invalid pattern '{pattern_config.get('pattern', 'unknown')}': {e}")
        except Exception as e:
            print(f"Error processing pattern: {e}")
        
        return matches
    
    def _normalize_value(self, value: str, pattern_config: Dict[str, Any], full_match: str) -> str:
        """Normalize extracted values based on pattern configuration."""
        unit = pattern_config.get("unit", "")
        
        if unit == "kg" and "." in value:
            value = value.replace(",", ".")
        elif unit == "cm":
            # Convert meters to cm if needed
            if "м" in full_match and float(value) < 10:
                value = str(int(float(value) * 100))
                print(f"  📏 Converted to cm: {value}")
        
        return value
    
    def is_information_providing(self, text: str) -> bool:
        """Determine if user is providing information vs asking questions."""
        providing_score = sum(1 for pattern in self.info_providing_indicators 
                            if re.search(pattern, text, re.IGNORECASE))
        question_score = sum(1 for pattern in self.question_indicators 
                           if re.search(pattern, text, re.IGNORECASE))
        
        # If user provides specific data (numbers + units), it's likely information providing
        has_data = bool(re.search(r"\d+\s*(?:кг|см|лет|%|kg|cm|years|ft|lbs)", text, re.IGNORECASE))
        
        return providing_score > question_score or has_data
    
    def is_data_query(self, text: str) -> bool:
        """Determine if user is asking for their stored data."""
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in self.data_query_patterns)


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