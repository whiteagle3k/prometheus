"""Context manager for conversation continuity and memory handling."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional


class ConversationContext:
    """Manages conversation context and continuity."""
    
    def __init__(self, identity_config: Dict[str, Any]):
        """Initialize the context manager with identity configuration."""
        self.identity_config = identity_config
        self.conversation_config = identity_config.get("conversation_management", {})
        self.routing_config = identity_config.get("routing_configuration", {})
        
        # Conversation state
        self.user_name: Optional[str] = None
        self.current_topic: Optional[str] = None
        self.interaction_count: int = 0
        self.last_user_language: str = "en"
        
        # Rolling conversation window
        self.context_window_size = self.conversation_config.get("context_window_size", 3)
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Topic tracking
        self.topic_stack: List[str] = []
        self.entity_mentions: Dict[str, int] = {}  # Track frequently mentioned entities
        
    def update_from_input(self, user_input: str) -> None:
        """Update context based on new user input."""
        self.interaction_count += 1
        
        # Detect language
        self.last_user_language = self._detect_language(user_input)
        
        # Extract and update user name if mentioned
        self._extract_user_name(user_input)
        
        # Track topics and entities
        self._update_topic_tracking(user_input)
        
        # Add to conversation history
        self.conversation_history.append({
            "type": "user_input",
            "content": user_input,
            "timestamp": datetime.now().isoformat(),
            "language": self.last_user_language,
            "detected_entities": self._extract_entities(user_input)
        })
        
        # Trim history to context window
        if len(self.conversation_history) > self.context_window_size * 2:  # *2 for user+assistant pairs
            self.conversation_history = self.conversation_history[-self.context_window_size * 2:]
    
    def add_response(self, response: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add assistant response to context."""
        self.conversation_history.append({
            "type": "assistant_response",
            "content": response,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        
        # Extract topics from our own response for better tracking
        self._update_topic_tracking(response, is_assistant=True)
    
    def build_context_prompt(self, user_input: str) -> str:
        """Build a context-aware prompt for the current input."""
        # Check if this is a reference question first
        reference_info = self._detect_references(user_input)
        
        if reference_info:
            # This is a continuation/reference question
            return self._build_reference_prompt(user_input, reference_info)
        
        # Check if user is asking about themselves
        if self._is_self_reference_question(user_input):
            return self._build_self_reference_prompt(user_input)
        
        # Check if this is a simple greeting that shouldn't have context
        if self._is_simple_greeting(user_input):
            return user_input
        
        # Build context-enhanced prompt
        context_parts = []
        
        # Add user identity if known and relevant
        if self.user_name:
            if self.last_user_language == "ru":
                context_parts.append(f"Пользователя зовут {self.user_name}.")
            else:
                context_parts.append(f"User's name is {self.user_name}.")
        
        # Add relevant conversation context (especially important for external->local transitions)
        conversation_context = self._build_conversation_context()
        if conversation_context:
            context_parts.append(conversation_context)
        
        # Build final prompt
        if context_parts:
            context_str = " ".join(context_parts)
            if self.last_user_language == "ru":
                return f"Контекст: {context_str}\n\nВопрос: {user_input}"
            else:
                return f"Context: {context_str}\n\nQuestion: {user_input}"
        
        return user_input
    
    def _detect_language(self, text: str) -> str:
        """Detect the language of the input text."""
        # Simple Cyrillic detection
        cyrillic_chars = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
        total_chars = len([char for char in text if char.isalpha()])
        
        if total_chars > 0 and cyrillic_chars / total_chars > 0.3:
            return "ru"
        return "en"
    
    def _extract_user_name(self, user_input: str) -> None:
        """Extract user name from input if mentioned."""
        patterns = self.conversation_config.get("name_extraction", {}).get("patterns", [])
        
        for pattern in patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                self.user_name = match.group(1).capitalize()
                break
    
    def _update_topic_tracking(self, text: str, is_assistant: bool = False) -> None:
        """Update topic tracking from text."""
        # Extract important words/entities
        entities = self._extract_entities(text)
        
        # Update entity frequency
        for entity in entities:
            self.entity_mentions[entity] = self.entity_mentions.get(entity, 0) + 1
        
        # Update current topic (most frequently mentioned entity recently)
        if entities:
            # Weight recent entities more heavily
            recent_weight = 2 if not is_assistant else 1
            for entity in entities:
                self.entity_mentions[entity] = self.entity_mentions.get(entity, 0) + recent_weight
            
            # Set current topic to most frequent recent entity
            sorted_entities = sorted(self.entity_mentions.items(), key=lambda x: x[1], reverse=True)
            if sorted_entities:
                self.current_topic = sorted_entities[0][0]
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract potential entities/topics from text."""
        # Simple entity extraction - important words longer than 3 chars
        words = re.findall(r'\b\w{4,}\b', text.lower())
        
        # Filter out common words
        common_words = {"that", "this", "they", "them", "were", "been", "have", "will", "your", "with",
                       "это", "эти", "были", "есть", "будет", "ваш", "для", "как", "что"}
        
        entities = [word for word in words if word not in common_words]
        return entities[:5]  # Return top 5 to avoid noise
    
    def _detect_references(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Detect if user input contains references to previous conversation."""
        user_lower = user_input.lower()
        
        # Check for pronouns
        pronouns = self.conversation_config.get("reference_detection", {}).get("pronouns", [])
        has_pronouns = any(pronoun in user_lower for pronoun in pronouns)
        
        # Check for continuation phrases
        continuation_phrases = self.conversation_config.get("reference_detection", {}).get("continuation_phrases", [])
        has_continuation = any(phrase in user_lower for phrase in continuation_phrases)
        
        if has_pronouns or has_continuation:
            # Find what they might be referring to
            reference_target = self._find_reference_target(user_input)
            return {
                "has_pronouns": has_pronouns,
                "has_continuation": has_continuation,
                "target": reference_target,
                "current_topic": self.current_topic
            }
        
        return None
    
    def _find_reference_target(self, user_input: str) -> Optional[str]:
        """Find what the user is likely referring to."""
        # Look in recent conversation for the most likely target
        if len(self.conversation_history) >= 2:
            # Check last assistant response for main topic
            last_response = self.conversation_history[-1]
            if last_response["type"] == "assistant_response":
                response_entities = self._extract_entities(last_response["content"])
                if response_entities:
                    return response_entities[0]  # Most prominent entity in last response
        
        # Fallback to current tracked topic
        return self.current_topic
    
    def _is_self_reference_question(self, user_input: str) -> bool:
        """Check if user is asking about themselves (needs context)."""
        context_questions = self.conversation_config.get("context_questions", [])
        user_lower = user_input.lower()
        return any(question in user_lower for question in context_questions)
    
    def _is_simple_greeting(self, user_input: str) -> bool:
        """Check if this is a simple greeting that shouldn't have context."""
        simple_greetings = self.routing_config.get("simple_conversation", [])
        user_lower = user_input.lower()
        
        is_greeting = any(greeting in user_lower for greeting in simple_greetings)
        
        # But exclude self-reference questions even if they contain greeting words
        is_self_reference = self._is_self_reference_question(user_input)
        
        return is_greeting and not is_self_reference
    
    def _build_reference_prompt(self, user_input: str, reference_info: Dict[str, Any]) -> str:
        """Build a prompt for reference/continuation questions."""
        target = reference_info.get("target")
        
        if target:
            if self.last_user_language == "ru":
                context_instruction = f"Пользователь спрашивает о '{target}' из предыдущего разговора."
            else:
                context_instruction = f"User is asking about '{target}' from the previous conversation."
        else:
            if self.last_user_language == "ru":
                context_instruction = "Пользователь продолжает предыдущий разговор."
            else:
                context_instruction = "User is continuing the previous conversation."
        
        # Add recent conversation context
        conversation_context = self._build_conversation_context(max_exchanges=2)
        
        if self.last_user_language == "ru":
            return f"{context_instruction}\n\n{conversation_context}\n\nНовый вопрос: {user_input}"
        else:
            return f"{context_instruction}\n\n{conversation_context}\n\nNew question: {user_input}"
    
    def _build_self_reference_prompt(self, user_input: str) -> str:
        """Build a prompt for self-reference questions."""
        if self.user_name:
            if self.last_user_language == "ru":
                context_instruction = f"ВАЖНО: Пользователя зовут {self.user_name}."
            else:
                context_instruction = f"IMPORTANT: The user's name is {self.user_name}."
            
            return f"{context_instruction}\n\nВопрос: {user_input}"
        
        return user_input
    
    def _build_conversation_context(self, max_exchanges: int = 2) -> str:
        """Build a summary of recent conversation."""
        if not self.conversation_history:
            return ""
        
        context_parts = []
        exchanges = 0
        
        # Work backwards through history to get recent exchanges
        i = len(self.conversation_history) - 1
        current_exchange = []
        
        while i >= 0 and exchanges < max_exchanges:
            entry = self.conversation_history[i]
            
            if entry["type"] == "user_input":
                if current_exchange:
                    # We have a complete exchange (assistant response + user input)
                    user_part = entry["content"][:100]
                    assistant_part = current_exchange[0]["content"][:100]
                    
                    if self.last_user_language == "ru":
                        context_parts.insert(0, f"Пользователь: {user_part}\nАлетейя: {assistant_part}")
                    else:
                        context_parts.insert(0, f"User: {user_part}\nAletheia: {assistant_part}")
                    
                    exchanges += 1
                    current_exchange = []
                else:
                    # Just a user input without response yet
                    break
            elif entry["type"] == "assistant_response":
                current_exchange = [entry]
            
            i -= 1
        
        if context_parts:
            if self.last_user_language == "ru":
                return "Предыдущий разговор:\n" + "\n\n".join(context_parts)
            else:
                return "Previous conversation:\n" + "\n\n".join(context_parts)
        
        return ""
    
    def should_use_external_routing(self, user_input: str) -> bool:
        """Determine if input should be routed to external LLM."""
        factual_indicators = self.routing_config.get("factual_indicators", [])
        min_words = self.identity_config.get("operational_guidelines", {}).get("routing_policy", {}).get("thresholds", {}).get("factual_question_min_words", 5)
        
        user_lower = user_input.lower()
        is_factual = any(indicator in user_lower for indicator in factual_indicators)
        is_substantial = len(user_input.split()) > min_words
        
        return is_factual and is_substantial
    
    def should_plan_task(self, user_input: str) -> bool:
        """Determine if task requires planning."""
        planning_indicators = self.routing_config.get("planning_indicators", [])
        dismissive_phrases = self.routing_config.get("dismissive_phrases", [])
        
        user_lower = user_input.lower()
        
        # Check for planning indicators
        has_planning_keywords = any(indicator in user_lower for indicator in planning_indicators)
        
        # Check if it's a dismissive phrase (but not if it's also a continuation phrase)
        continuation_phrases = self.conversation_config.get("reference_detection", {}).get("continuation_phrases", [])
        is_continuation = any(phrase in user_lower for phrase in continuation_phrases)
        
        # Only consider dismissive if it's not a continuation
        is_dismissive = False
        if not is_continuation:
            is_dismissive = any(
                re.search(r'\b' + re.escape(phrase) + r'\b', user_lower) 
                for phrase in dismissive_phrases if len(phrase.split()) == 1
            ) or any(
                phrase in user_lower 
                for phrase in dismissive_phrases if len(phrase.split()) > 1
            )
        
        # Very complex questions
        is_very_complex = len(user_input.split()) > 30
        
        # Multiple parts/questions
        has_multiple_parts = (
            user_input.count('?') > 1 or
            any(sep in user_input for sep in [" then ", " next ", " after that ", " затем ", " потом ", " далее "])
        )
        
        return (has_planning_keywords or is_very_complex or has_multiple_parts) and not (is_dismissive and len(user_input.split()) < 10)
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of current context state."""
        return {
            "user_name": self.user_name,
            "current_topic": self.current_topic,
            "interaction_count": self.interaction_count,
            "language": self.last_user_language,
            "conversation_length": len(self.conversation_history),
            "top_entities": dict(sorted(self.entity_mentions.items(), key=lambda x: x[1], reverse=True)[:3])
        } 