"""Context management for conversation history and continuity."""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..processing.pipeline import create_context_analysis_pipeline
from ..processing.extractors import EntityExtractor, NameExtractor
from ..processing.detectors import ReferenceDetector


logger = logging.getLogger(__name__)


class ContextManager:
    """Manages conversation context, user profiles, and continuity."""

    def __init__(self, identity_config=None):
        """Initialize context manager."""
        self.identity_config = identity_config
        self.user_profiles: Dict[str, Dict[str, Any]] = {}
        self.conversations: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.current_topics: Dict[str, str] = {}
        self.extracted_entities: Dict[str, List[str]] = defaultdict(list)
        
        # Initialize processing pipeline
        self.context_pipeline = create_context_analysis_pipeline()
        
        # Initialize individual processors for specific tasks
        self.entity_extractor = EntityExtractor()
        self.name_extractor = NameExtractor()
        self.reference_detector = ReferenceDetector()
        
        # Properties expected by orchestrator
        self.current_topic: Optional[str] = None
        self.user_name: Optional[str] = None
        self.interaction_count: int = 0
        self.last_user_language: str = "en"
        self.conversation_history: List[Dict[str, Any]] = []

    def add_message(self, user_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a message to conversation history."""
        timestamp = datetime.now().isoformat()
        
        message = {
            "role": role,
            "content": content,
            "timestamp": timestamp,
            "metadata": metadata or {}
        }
        
        self.conversations[user_id].append(message)
        
        # Process context for user messages
        if role == "user":
            self._process_user_context(user_id, content)

    def _process_user_context(self, user_id: str, content: str) -> None:
        """Process user message to extract context information."""
        
        # Run full context analysis pipeline
        pipeline_result = self.context_pipeline.process(content)
        
        # Extract specific results
        for proc_result in pipeline_result["results"]:
            proc_name = proc_result["processor"]
            result = proc_result["result"]
            
            if proc_name == "EntityExtractor" and result.success:
                entities = result.data
                if entities:
                    self.extracted_entities[user_id].extend(entities)
                    # Keep only last 20 entities to avoid memory bloat
                    self.extracted_entities[user_id] = self.extracted_entities[user_id][-20:]
                    
                    # Update current topic with the most significant entity
                    self.current_topics[user_id] = entities[0]
            
            elif proc_name == "NameExtractor" and result.success:
                names = result.data
                if names:
                    # Store user name in profile
                    if user_id not in self.user_profiles:
                        self.user_profiles[user_id] = {}
                    self.user_profiles[user_id]["name"] = names[0]

    def get_conversation_history(
        self, 
        user_id: str, 
        limit: int = 10,
        include_system: bool = False
    ) -> List[Dict[str, Any]]:
        """Get recent conversation history for a user."""
        messages = self.conversations[user_id]
        
        if not include_system:
            messages = [msg for msg in messages if msg["role"] != "system"]
        
        return messages[-limit:] if limit > 0 else messages

    def get_context_summary(self, user_id: str, current_input: str) -> Dict[str, Any]:
        """Build comprehensive context summary for the current interaction."""
        
        # Check if current input is a reference question
        ref_result = self.reference_detector.process(current_input)
        is_reference = ref_result.data.get("has_references", False) if ref_result.success else False
        
        # Get conversation history
        recent_messages = self.get_conversation_history(user_id, limit=5)
        
        # Build context information
        context = {
            "user_id": user_id,
            "current_input": current_input,
            "is_reference_question": is_reference,
            "conversation_length": len(self.conversations[user_id]),
            "has_history": len(recent_messages) > 0,
        }
        
        # Add user profile information
        if user_id in self.user_profiles:
            context["user_profile"] = self.user_profiles[user_id].copy()
        
        # Add topic information
        if user_id in self.current_topics:
            context["current_topic"] = self.current_topics[user_id]
        
        # Add recent entities
        if user_id in self.extracted_entities:
            context["recent_entities"] = self.extracted_entities[user_id][-5:]  # Last 5 entities
        
        # If this is a reference question, build context from history
        if is_reference and recent_messages:
            context["reference_context"] = self._build_reference_context(recent_messages, current_input)
        
        # Add recent conversation
        if recent_messages:
            context["recent_conversation"] = [
                {"role": msg["role"], "content": msg["content"][:200]}  # Truncate for summary
                for msg in recent_messages[-3:]  # Last 3 messages
            ]
        
        return context

    def _build_reference_context(self, recent_messages: List[Dict[str, Any]], current_input: str) -> str:
        """Build context summary for reference questions."""
        
        # Extract entities from current input to understand what user is referring to
        entity_result = self.entity_extractor.process(current_input)
        current_entities = entity_result.data if entity_result.success else []
        
        context_parts = []
        
        # Look through recent messages for relevant context
        for message in reversed(recent_messages[-5:]):  # Check last 5 messages
            if message["role"] == "assistant":
                content = message["content"]
                
                # Check if this message contains entities from current input
                content_lower = content.lower()
                
                # Find relevant context
                if current_entities:
                    for entity in current_entities:
                        if entity.lower() in content_lower:
                            # Add relevant portion of the message
                            context_parts.append(f"Ранее обсуждали {entity}: {content[:150]}...")
                            break
                else:
                    # Generic reference - include most recent assistant response
                    context_parts.append(f"Предыдущий ответ: {content[:150]}...")
                    break
        
        # If no specific context found but we have recent entities, mention them
        if not context_parts and hasattr(self, 'extracted_entities'):
            recent_entities = self.extracted_entities.get(message.get("user_id", ""), [])
            if recent_entities:
                entities_text = ", ".join(recent_entities[-3:])
                context_parts.append(f"Недавно обсуждали: {entities_text}")
        
        return " ".join(context_parts) if context_parts else ""

    def clear_user_context(self, user_id: str) -> None:
        """Clear all context for a specific user."""
        if user_id in self.conversations:
            del self.conversations[user_id]
        if user_id in self.user_profiles:
            del self.user_profiles[user_id]
        if user_id in self.current_topics:
            del self.current_topics[user_id]
        if user_id in self.extracted_entities:
            del self.extracted_entities[user_id]

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile information."""
        return self.user_profiles.get(user_id)

    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> None:
        """Update user profile information."""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {}
        self.user_profiles[user_id].update(updates)

    def get_conversation_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about the conversation."""
        messages = self.conversations[user_id]
        
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]
        
        return {
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "entities_extracted": len(self.extracted_entities.get(user_id, [])),
            "current_topic": self.current_topics.get(user_id),
            "has_profile": user_id in self.user_profiles
        }

    def should_use_context(self, user_id: str, current_input: str) -> bool:
        """Determine if context should be used for this interaction."""
        
        # Always use context if it's a reference question
        ref_result = self.reference_detector.process(current_input)
        if ref_result.success and ref_result.data.get("has_references", False):
            return True
        
        # Use context if we have a meaningful conversation history
        if len(self.conversations[user_id]) > 2:
            return True
        
        # Use context if we have user profile information
        if user_id in self.user_profiles and self.user_profiles[user_id]:
            return True
        
        return False

    def update_from_input(self, user_input: str) -> None:
        """Update context from user input (orchestrator compatibility)."""
        self.interaction_count += 1
        
        # Simple language detection
        if any(char in user_input.lower() for char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"):
            self.last_user_language = "ru"
        else:
            self.last_user_language = "en"
        
        # Check if this is a reference question
        ref_result = self.reference_detector.process(user_input)
        is_reference = ref_result.success and ref_result.data.get("has_references", False)
        
        # Extract entities and update current topic (but preserve topic for reference questions)
        entity_result = self.entity_extractor.process(user_input)
        if entity_result.success and entity_result.data:
            new_entities = entity_result.data
            
            # Don't overwrite current topic with reference words if this is a reference question
            if not is_reference or not self.current_topic:
                # Only update topic if it's not a reference question or we don't have a topic yet
                self.current_topic = new_entities[0]
            else:
                # For reference questions, only update if the new entity is more specific
                # (longer than current topic and not a common reference word)
                reference_words = {"это", "то", "такое", "когда", "где", "что", "произошло", "случилось"}
                if (new_entities[0].lower() not in reference_words and 
                    len(new_entities[0]) > len(self.current_topic)):
                    self.current_topic = new_entities[0]
        
        # Extract user name
        name_result = self.name_extractor.process(user_input)
        if name_result.success and name_result.data and not self.user_name:
            self.user_name = name_result.data[0]
        
        # Add to conversation history with 'type' field expected by orchestrator
        self.conversation_history.append({
            "type": "user_input",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })

    def should_plan_task(self, user_input: str) -> bool:
        """Determine if task needs planning (orchestrator compatibility)."""
        from ..processing.detectors import ComplexityDetector
        complexity_detector = ComplexityDetector()
        return complexity_detector.detect(user_input)

    def add_response(self, response: str, execution_details: Optional[Dict[str, Any]] = None) -> None:
        """Add response to context (orchestrator compatibility)."""
        self.conversation_history.append({
            "type": "assistant_response", 
            "content": response,
            "timestamp": datetime.now().isoformat(),
            "execution_details": execution_details or {}
        })

    def build_context_prompt(self, user_input: str) -> str:
        """Build context prompt for LLM (orchestrator compatibility)."""
        context_parts = []
        
        if self.user_name:
            context_parts.append(f"User name: {self.user_name}")
        
        if self.current_topic:
            context_parts.append(f"Current topic: {self.current_topic}")
        
        # Add recent conversation context
        if len(self.conversation_history) > 0:
            recent = self.conversation_history[-3:]  # Last 3 exchanges
            for entry in recent:
                if entry["type"] == "user_input":
                    context_parts.append(f"Previous question: {entry['content'][:100]}")
                elif entry["type"] == "assistant_response":
                    context_parts.append(f"Previous response: {entry['content'][:100]}")
        
        return "\n".join(context_parts) if context_parts else ""

    def get_context_summary(self) -> Dict[str, Any]:
        """Get context summary (orchestrator compatibility)."""
        return {
            "user_name": self.user_name,
            "current_topic": self.current_topic,
            "interaction_count": self.interaction_count,
            "language": self.last_user_language,
            "conversation_length": len(self.conversation_history),
            "has_context": len(self.conversation_history) > 0
        }


# Compatibility alias for orchestrator
ConversationContext = ContextManager 