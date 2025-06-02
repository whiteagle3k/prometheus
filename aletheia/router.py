"""Main router for the Aletheia system - orchestrates all components."""

import asyncio
import re
import traceback
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional
import time

from .config import config
from .identity.loader import (
    load_identity_config, 
    get_routing_config, 
    get_conversation_config, 
    get_validation_config
)
from .llm.local_llm import LocalLLM
from .llm.providers import ExternalLLMManager
from .memory.hierarchical_store import HierarchicalMemoryStore
from .memory.vector_store import VectorStore
from .agent.context_manager import ConversationContext


class Router:
    """Main router for the Aletheia system.
    
    Orchestrates the interaction between local LLM, external LLM providers,
    memory systems, and conversation management using proper OOP architecture.
    """

    def __init__(self) -> None:
        """Initialize router with local LLM and external providers."""
        print("🚀 Initializing Aletheia Router...")
        
        # Suppress asyncio task exceptions from external API clients
        warnings.filterwarnings("ignore", message=".*AsyncHttpxClientWrapper.*", category=Warning)

        # Initialize core components
        self.local_llm = LocalLLM()
        
        # Use new OOP provider architecture
        self.external_manager = ExternalLLMManager()
        
        # Memory and other components
        self.vector_store = VectorStore()
        self.memory_store = HierarchicalMemoryStore(self.vector_store) 
        self.conversation_context = ConversationContext()
        
        # Load identity configuration
        self.identity_config = load_identity_config()
        self.routing_config = get_routing_config()
        self.conversation_config = get_conversation_config()
        self.validation_config = get_validation_config()
        
        # Session management
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print("🤖 Router initialized with OOP provider architecture")

    async def process_input(self, user_input: str) -> Dict[str, Any]:
        """Process user input and return response."""
        try:
            start_time = time.time()
            
            # Update conversation context
            self.conversation_context.add_user_message(user_input)
            
            # Build context for response generation
            conversation_context = await self._build_conversation_context(user_input)
            
            # Retrieve relevant memories
            memories = await self.memory_store.search_memories(user_input)
            
            # Decide on routing and generate response
            response, execution_details = await self._generate_response(
                user_input, conversation_context, memories
            )
            
            # Store the interaction in memory
            await self._store_interaction(user_input, response, execution_details)
            
            # Update conversation context with response
            self.conversation_context.add_assistant_message(response)
            
            processing_time = time.time() - start_time
            
            return {
                "response": response,
                "execution_details": execution_details,
                "processing_time": processing_time,
                "session_id": self.session_id,
            }
            
        except Exception as e:
            error_msg = f"Router processing error: {str(e)}"
            print(f"❌ {error_msg}")
            traceback.print_exc()
            
            return {
                "response": "I encountered an error processing your request. Please try again.",
                "error": error_msg,
                "execution_details": {"route_used": "error"},
            }

    async def _build_conversation_context(self, user_input: str) -> str:
        """Build comprehensive conversation context."""
        # Get recent conversation history
        history = self.conversation_context.get_recent_exchanges(limit=10)
        
        # Build context summary
        context_parts = []
        
        if history:
            context_parts.append("Recent conversation:")
            for exchange in history[-5:]:  # Last 5 exchanges
                context_parts.append(f"User: {exchange.get('user', '')}")
                context_parts.append(f"Assistant: {exchange.get('assistant', '')}")
        
        # Add user identification if available
        user_name = self.conversation_context.get_user_name()
        if user_name:
            context_parts.append(f"User name: {user_name}")
        
        return "\n".join(context_parts)

    async def _generate_response(
        self, 
        user_input: str, 
        conversation_context: str, 
        memories: List[Dict[str, Any]]
    ) -> tuple[str, Dict[str, Any]]:
        """Generate response using appropriate LLM."""
        
        # Check if we should use external LLM
        should_use_external = await self._should_route_external(user_input, conversation_context)
        
        execution_details = {
            "route_used": "external" if should_use_external else "local",
            "memories_retrieved": len(memories),
            "context_used": bool(conversation_context),
        }
        
        if should_use_external:
            # Use external LLM with new architecture
            response, external_metadata = await self._consult_external_llm(
                user_input, conversation_context, memories
            )
            execution_details.update(external_metadata)
        else:
            # Use local LLM
            response = await self._generate_local_response(
                user_input, conversation_context, memories
            )
            execution_details["provider"] = "local"
        
        return response, execution_details

    async def _should_route_external(self, user_input: str, context: str) -> bool:
        """Determine if we should route to external LLM."""
        # Estimate token count
        total_text = user_input + context
        estimated_tokens = len(total_text.split()) * 1.3  # Rough estimation
        
        # Route to external if over threshold
        threshold = self.routing_config.get("external_threshold_tokens", 1024)
        if estimated_tokens > threshold:
            return True
        
        # Route to external for complex tasks
        complex_indicators = self.routing_config.get("planning_indicators", [])
        if any(indicator in user_input.lower() for indicator in complex_indicators):
            return True
        
        # Default to local
        return False

    async def _consult_external_llm(
        self,
        user_input: str,
        conversation_context: str,
        memories: List[Dict[str, Any]],
    ) -> tuple[str, Dict[str, Any]]:
        """Consult external LLM using the new provider architecture."""
        try:
            # Get the best available provider
            provider = await self.external_manager.get_best_available()
            if not provider:
                # Fallback to local
                response = await self._generate_local_response(user_input, conversation_context, memories)
                return response, {
                    "provider": "local_fallback",
                    "reason": "no_external_providers_available"
                }

            # Get provider info for metadata
            provider_info = provider.get_model_info()
            
            # Prepare enhanced context
            enhanced_context = await self._prepare_external_context(
                user_input, conversation_context, memories
            )
            
            # Generate response using the provider
            response = await provider.generate(
                prompt=enhanced_context,
                max_tokens=1000,
                temperature=0.7,
                system_prompt=self._get_external_system_prompt()
            )
            
            # Estimate tokens and cost
            input_tokens = await provider.count_tokens(enhanced_context)
            output_tokens = await provider.count_tokens(response)
            estimated_cost = provider.estimate_cost(input_tokens, output_tokens)
            
            metadata = {
                "provider": provider_info.get("provider", "unknown"),
                "model": provider_info.get("model", "unknown"),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost": estimated_cost,
                "capabilities": provider_info.get("capabilities", {}),
            }
            
            return response, metadata
            
        except Exception as e:
            print(f"❌ External LLM error: {e}")
            # Fallback to local
            response = await self._generate_local_response(user_input, conversation_context, memories)
            return response, {
                "provider": "local_fallback",
                "error": str(e)
            }

    async def _prepare_external_context(
        self, 
        user_input: str, 
        conversation_context: str, 
        memories: List[Dict[str, Any]]
    ) -> str:
        """Prepare enhanced context for external LLM."""
        context_parts = [
            f"User Query: {user_input}",
        ]
        
        if conversation_context:
            context_parts.append(f"Conversation Context:\n{conversation_context}")
        
        if memories:
            context_parts.append("Relevant Memories:")
            for memory in memories[:5]:  # Top 5 memories
                context_parts.append(f"- {memory.get('content', '')}")
        
        context_parts.append(
            "Please provide a helpful, accurate response in the same style as the conversation context. "
            "Be concise and direct (1-2 sentences for simple facts)."
        )
        
        return "\n\n".join(context_parts)

    def _get_external_system_prompt(self) -> str:
        """Get system prompt for external LLM."""
        identity = self.identity_config
        name = identity.get("name", "Aletheia")
        summary = identity.get("identity", {}).get("summary", "")
        
        return f"""You are {name}, {summary}. 
        
Respond in the same style as shown in the conversation context. 
Be helpful, accurate, and maintain the established conversational tone.
For simple factual questions, provide concise 1-2 sentence responses.
Use appropriate language based on the conversation context."""

    async def _generate_local_response(
        self, 
        user_input: str, 
        conversation_context: str, 
        memories: List[Dict[str, Any]]
    ) -> str:
        """Generate response using local LLM."""
        try:
            # Prepare context for local LLM
            prompt_parts = [user_input]
            
            if conversation_context:
                prompt_parts.insert(0, f"Context: {conversation_context}")
            
            if memories:
                memory_context = "Relevant information:\n"
                for memory in memories[:3]:  # Top 3 memories
                    memory_context += f"- {memory.get('content', '')}\n"
                prompt_parts.insert(-1, memory_context)
            
            full_prompt = "\n\n".join(prompt_parts)
            
            # Generate response
            response = await self.local_llm.generate(
                prompt=full_prompt,
                max_tokens=512,
                temperature=0.7
            )
            
            return response
            
        except Exception as e:
            print(f"❌ Local LLM error: {e}")
            return "I'm experiencing technical difficulties. Please try again."

    async def _store_interaction(
        self, 
        user_input: str, 
        response: str, 
        execution_details: Dict[str, Any]
    ) -> None:
        """Store the interaction in memory."""
        try:
            # Create memory entry
            interaction_data = {
                "user_input": user_input,
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "execution_details": execution_details,
            }
            
            # Store in hierarchical memory
            await self.memory_store.store_memory(
                content=f"User: {user_input}\nAssistant: {response}",
                metadata=interaction_data
            )
            
        except Exception as e:
            print(f"⚠️ Memory storage error: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """Get router status and health information."""
        try:
            # Get provider health status
            provider_health = await self.external_manager.health_check_all()
            provider_info = await self.external_manager.get_all_provider_info()
            
            # Get memory stats
            memory_stats = await self.memory_store.get_memory_stats()
            
            # Get local LLM status
            local_available = await self.local_llm.is_available()
            
            return {
                "session_id": self.session_id,
                "local_llm": {
                    "available": local_available,
                    "context_size": self.local_llm.get_context_size(),
                },
                "external_providers": {
                    "health": provider_health,
                    "details": provider_info,
                    "configured_count": len(self.external_manager.list_available_providers()),
                },
                "memory": memory_stats,
                "conversation": {
                    "exchanges_count": len(self.conversation_context.get_recent_exchanges()),
                    "user_name": self.conversation_context.get_user_name(),
                },
                "configuration": {
                    "routing": self.routing_config,
                    "conversation": self.conversation_config,
                },
            }
            
        except Exception as e:
            return {"error": f"Status check failed: {e}"}

    async def reset_session(self) -> None:
        """Reset the current session."""
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.conversation_context.reset()
        print(f"🔄 Session reset. New session ID: {self.session_id}") 