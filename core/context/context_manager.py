"""Context management for conversation history and continuity."""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import re

from ..processing.pipeline import create_context_analysis_pipeline
from ..processing.extractors import EntityExtractor, NameExtractor
from ..processing.detectors import ReferenceDetector, ComplexityDetector
from ..processing.cleaners import ChainOfThoughtExtractor
from ..processing.config import get_processor_config


logger = logging.getLogger(__name__)


class RunningSummary:
    """Manages a running summary of conversation context using LLM-based compression."""
    
    def __init__(self, user_id: str = "default", max_tokens: int = 300):
        """Initialize running summary for a user."""
        self.user_id = user_id
        self.max_tokens = max_tokens
        self.summary = ""
        self.last_updated = datetime.now()
        self.exchange_count = 0
    
    def is_empty(self) -> bool:
        """Check if summary is empty."""
        return not self.summary.strip()
    
    def get_summary(self) -> str:
        """Get current running summary."""
        if self.is_empty():
            return f"New conversation with user {self.user_id}."
        return self.summary
    
    def set_summary(self, new_summary: str) -> None:
        """Update the running summary."""
        self.summary = new_summary.strip()
        self.last_updated = datetime.now()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            "user_id": self.user_id,
            "summary_length": len(self.summary),
            "estimated_tokens": len(self.summary.split()) * 1.3,  # Rough token estimate
            "last_updated": self.last_updated.isoformat(),
            "exchange_count": self.exchange_count,
            "is_empty": self.is_empty()
        }


class ConversationContext:
    """Enhanced conversation context with LLM-managed running summaries."""

    def __init__(self, identity_config=None):
        """Initialize context manager with running summary approach."""
        self.identity_config = identity_config
        
        # Running summaries per user (multi-user support)
        self.running_summaries: Dict[str, RunningSummary] = {}
        
        # Current session context
        self.current_user_id = "default"
        self.session_id = None
        self.interaction_count = 0
        self.last_user_language = "en"
        
        # Extractors for basic information (still needed for names, etc.)
        self.entity_extractor = EntityExtractor()
        self.name_extractor = NameExtractor()
        
        # Initialize processing components for pattern handling
        self.complexity_detector = ComplexityDetector()
        self.cot_extractor = ChainOfThoughtExtractor()
        
        # Episode storage for L2 retrieval (full conversation pairs)
        self.episodes: List[Dict[str, Any]] = []
        self.max_episodes = 50  # Keep last 50 full exchanges for RAG search
        
        logger.info("🧠 Initialized LLM-managed context system")

    def get_or_create_summary(self, user_id: str = None) -> RunningSummary:
        """Get or create running summary for a user."""
        if user_id is None:
            user_id = self.current_user_id
            
        if user_id not in self.running_summaries:
            self.running_summaries[user_id] = RunningSummary(user_id)
            logger.info(f"📝 Created new running summary for user: {user_id}")
            
        return self.running_summaries[user_id]

    def update_from_input(self, user_input: str, user_id: Optional[str] = None) -> None:
        """Extract basic information from user input (names, language) and manage user sessions."""
        self.interaction_count += 1
        
        # Handle user_id switching if provided
        if user_id and user_id != self.current_user_id:
            logger.info(f"👤 User session switch: {self.current_user_id} → {user_id}")
            self.current_user_id = user_id
        
        # Detect language
        is_russian = any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for char in user_input.lower())
        self.last_user_language = "ru" if is_russian else "en"
        
        # Extract user name if provided (for user switching)
        name_result = self.name_extractor.process(user_input)
        if name_result.success and name_result.data:
            # Check if this is a user introduction using processing config
            name_config = get_processor_config("name_extractor").parameters
            intro_patterns = name_config.get("introduction_patterns", [])
            
            if any(pattern in user_input.lower() for pattern in intro_patterns):
                new_user_id = name_result.data[0] if isinstance(name_result.data, list) else name_result.data
                if new_user_id != self.current_user_id:
                    logger.info(f"👤 User switch detected from input: {self.current_user_id} → {new_user_id}")
                    self.current_user_id = new_user_id

    async def update_summary_from_exchange(
        self, 
        user_input: str, 
        assistant_response: str, 
        local_llm=None
    ) -> None:
        """Update running summary based on new exchange using LLM compression."""
        
        summary = self.get_or_create_summary()
        summary.exchange_count += 1
        
        if not local_llm:
            # Fallback to simple append if no LLM available
            if summary.is_empty():
                summary.set_summary(f"User asked: {user_input[:100]}...")
            return
        
        # Build summary update prompt
        previous_summary = summary.get_summary()
        
        update_prompt = f"""Update the running conversation summary based on this new exchange.
Keep it concise (≤8 lines) but capture important context, facts, and the current topic.

PREVIOUS SUMMARY:
{previous_summary}

NEW EXCHANGE:
User: {user_input}
Assistant: {assistant_response}

UPDATED SUMMARY:
(Write a concise summary that captures the essence of the conversation so far)"""

        try:
            # Use local LLM to compress and update summary
            new_summary = await local_llm.generate(
                prompt=update_prompt,
                max_tokens=200,  # Keep summary concise
                temperature=0.3,  # Lower temperature for consistent summarization
                system_prompt="You are a conversation summarizer. Create concise summaries that preserve important context and facts."
            )
            
            # Estimate tokens and compress if too long
            estimated_tokens = len(new_summary.split()) * 1.3
            if estimated_tokens > summary.max_tokens:
                logger.info(f"📏 Summary too long ({estimated_tokens:.0f} tokens), compressing...")
                
                compression_prompt = f"""The summary is too long. Compress it to ≤150 words while keeping the most important information:

{new_summary}

COMPRESSED SUMMARY:"""
                
                compressed_summary = await local_llm.generate(
                    prompt=compression_prompt,
                    max_tokens=120,
                    temperature=0.2,
                    system_prompt="You are a text compressor. Preserve the most important information in fewer words."
                )
                
                summary.set_summary(compressed_summary)
                logger.info(f"✅ Summary compressed and updated for user {summary.user_id}")
            else:
                summary.set_summary(new_summary)
                logger.info(f"✅ Summary updated for user {summary.user_id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to update summary with LLM: {e}")
            # Fallback to simple update
            if summary.is_empty():
                summary.set_summary(f"Conversation about: {user_input[:50]}...")

    def add_episode(self, user_input: str, assistant_response: str, metadata: Dict[str, Any] = None) -> None:
        """Add full exchange to episode storage for RAG retrieval."""
        episode = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "assistant_response": assistant_response,
            "user_id": self.current_user_id,
            "interaction_id": self.interaction_count,
            "metadata": metadata or {}
        }
        
        self.episodes.append(episode)
        
        # Keep only recent episodes
        if len(self.episodes) > self.max_episodes:
            self.episodes = self.episodes[-self.max_episodes:]
            logger.debug(f"📚 Trimmed episodes to {len(self.episodes)}")

    def should_retrieve_episodes(self, user_input: str) -> bool:
        """Determine if we should retrieve episodes for context (for complex queries)."""
        # Simple heuristic: retrieve for longer, complex queries
        word_count = len(user_input.split())
        return word_count > 8  # Changed from >= 8 to > 8 for the test

    def search_relevant_episodes(self, user_input: str, max_episodes: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant episodes (simple text matching for now)."""
        if not self.episodes:
            return []
        
        # Simple relevance scoring based on common words
        user_words = set(user_input.lower().split())
        scored_episodes = []
        
        for episode in self.episodes:
            # Score based on word overlap
            episode_text = f"{episode['user_input']} {episode['assistant_response']}".lower()
            episode_words = set(episode_text.split())
            
            overlap = len(user_words.intersection(episode_words))
            if overlap > 0:
                scored_episodes.append((overlap, episode))
        
        # Sort by relevance and return top episodes
        scored_episodes.sort(key=lambda x: x[0], reverse=True)
        return [episode for _, episode in scored_episodes[:max_episodes]]

    def build_context_prompt(self, user_input: str, system_prompt: str = None) -> str:
        """Build structured prompt with running summary (new approach)."""
        
        summary = self.get_or_create_summary()
        
        # Base system prompt
        if not system_prompt:
            system_prompt = "You are Aletheia, a helpful and thoughtful AI assistant."
        
        # Build structured prompt without problematic <FINAL> tag
        context_prompt = f"""### SYSTEM
{system_prompt}

### RUNNING SUMMARY
{summary.get_summary()}

### CONVERSATION
User: {user_input}

Please respond with the following structure:
<BEGIN_THOUGHT>
(Brief reasoning about how to respond)
<END_THOUGHT>

(Your actual response here, without any additional tags)"""
        
        return context_prompt

    def extract_cot_and_response(self, raw_response: str) -> tuple[str, str]:
        """Extract Chain-of-Thought reasoning and final response from LLM output."""
        # Use the processing module for CoT extraction
        return self.cot_extractor.extract_cot_and_response(raw_response)

    @property
    def user_name(self) -> Optional[str]:
        """Get current user name (for compatibility)."""
        return self.current_user_id if self.current_user_id != "default" else None

    def get_context_summary(self) -> Dict[str, Any]:
        """Get context summary for diagnostics."""
        summary = self.get_or_create_summary()
        
        return {
            "current_user": self.current_user_id,
            "interaction_count": self.interaction_count,
            "language": self.last_user_language,
            "summary_stats": summary.get_stats(),
            "episodes_count": len(self.episodes),
            "total_users": len(self.running_summaries)
        }

    def should_plan_task(self, user_input: str) -> bool:
        """Determine if task needs planning using processing config patterns."""
        
        user_input_lower = user_input.lower()
        
        # Get explicit planning triggers from processing config
        complexity_config = get_processor_config("complexity_detector").parameters
        explicit_planning_triggers = complexity_config.get("explicit_planning_triggers", [])
        
        # Check for explicit planning language only
        has_explicit_planning = any(trigger in user_input_lower for trigger in explicit_planning_triggers)
        
        # Simple length check for procedural requests
        is_substantial_request = len(user_input.split()) >= 8
        
        # Only trigger planning for very explicit procedural requests
        return has_explicit_planning and is_substantial_request

    def add_response(self, response: str, execution_details: Dict[str, Any] = None) -> None:
        """Add assistant response to context (compatibility method)."""
        # This is handled by update_summary_from_exchange now
        pass


# Compatibility alias for orchestrator
ConversationContext = ConversationContext 