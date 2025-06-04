"""
Universal Telegram Bot

Provides Telegram interface for interacting with any entity.
Uses runtime registry to support multiple agents with per-chat entity switching.
"""

import asyncio
import logging
import os
import time

from prometheus_client import Counter, Histogram
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from core.runtime.registry import add_shutdown_handler, get_agent, get_running_agents

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Prometheus metrics with entity labels
route_decisions = Counter(
    "prometheus_route_decisions_total",
    "Route decisions made by agents",
    ["route", "user_id", "frontend", "entity"]
)

llm_processing_time = Histogram(
    "prometheus_llm_processing_seconds",
    "Time spent in LLM processing",
    ["route", "approach", "frontend", "entity"]
)

memory_operations = Counter(
    "prometheus_memory_operations_total",
    "Memory operations performed",
    ["operation_type", "user_id", "frontend", "entity"]
)

telegram_requests = Counter(
    "prometheus_telegram_requests_total",
    "Total Telegram requests processed",
    ["status", "user_id", "entity"]
)


class UniversalTelegramBot:
    """Universal Telegram bot interface with multi-entity support."""

    def __init__(self, token: str):
        """Initialize the Telegram bot."""
        self.token = token
        self.application: Application | None = None

        # Enhanced rate limiting with exponential back-pressure
        self.user_queues = {}
        self.user_timeouts = {}  # Track timeout periods per user
        self.max_queue_size = 2  # Max 2 pending requests per user
        self.base_timeout = 5    # Base timeout in seconds
        self.max_timeout = 300   # Max timeout (5 minutes)

        # Per-chat entity selection (chat_id -> entity_name)
        self.chat_entities: dict[str, str] = {}
        self.default_entity = "aletheia"

    def get_chat_entity(self, chat_id: str) -> str:
        """Get entity for specific chat."""
        return self.chat_entities.get(chat_id, self.default_entity)

    def set_chat_entity(self, chat_id: str, entity_name: str):
        """Set entity for specific chat."""
        self.chat_entities[chat_id] = entity_name
        logger.info(f"Chat {chat_id} switched to entity: {entity_name}")

    async def _get_user_queue(self, user_id: str) -> asyncio.Queue:
        """Get or create rate limiting queue for user."""
        if user_id not in self.user_queues:
            self.user_queues[user_id] = asyncio.Queue(maxsize=self.max_queue_size)
            self.user_timeouts[user_id] = 0
        return self.user_queues[user_id]

    def _calculate_timeout(self, user_id: str) -> float:
        """Calculate exponential back-pressure timeout."""
        current_timeout = self.user_timeouts.get(user_id, 0)
        if current_timeout == 0:
            new_timeout = self.base_timeout
        else:
            new_timeout = min(current_timeout * 2, self.max_timeout)

        self.user_timeouts[user_id] = new_timeout
        return new_timeout

    def _reset_timeout(self, user_id: str):
        """Reset timeout after successful processing."""
        self.user_timeouts[user_id] = 0

    async def _rate_limited_process(self, user_id: str, text: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process message with exponential back-pressure rate limiting."""
        try:
            queue = await self._get_user_queue(user_id)

            # Get entity for this chat
            chat_id = str(update.effective_chat.id)
            entity_name = self.get_chat_entity(chat_id)

            # Try to add to queue (non-blocking)
            try:
                queue.put_nowait((text, update, context, time.time(), entity_name))
            except asyncio.QueueFull:
                # Calculate exponential timeout
                timeout = self._calculate_timeout(user_id)

                await update.message.reply_text(
                    f"🚫 Слишком много запросов! Попробуйте через {timeout:.0f} секунд.\n"
                    f"🚫 Too many requests! Please try again in {timeout:.0f} seconds."
                )

                # Track rate limit hit
                telegram_requests.labels(status="rate_limited", user_id=user_id, entity=entity_name).inc()
                return

            # Process from queue
            text, update, context, request_time, entity_name = await queue.get()
            processing_start = time.time()

            # Get conversation context for continuation detection
            conversation_context = self._get_conversation_context(user_id)
            
            # Add current user message to conversation history
            self._add_to_conversation(user_id, "user", text)

            # Get agent instance from registry
            try:
                agent = await get_agent(entity_name)
            except ImportError:
                await update.message.reply_text(
                    f"❌ Entity '{entity_name}' not found!\n"
                    f"Available entities: {', '.join(get_running_agents())}\n"
                    f"Use /use <entity> to switch."
                )
                return

            # Process message with conversation context
            response = await agent.think(text, user_id=user_id, context=conversation_context)

            # Calculate processing time
            processing_time = time.time() - processing_start

            # Extract answer and metrics
            answer = str(response)
            route = "unknown"
            approach = "unknown"

            if isinstance(response, dict):
                if "result" in response:
                    answer = response["result"]

                execution_details = response.get("execution_details", {})
                route = execution_details.get("route_used", "unknown")
                approach = execution_details.get("approach", "unknown")

                # Update Prometheus metrics with entity label
                frontend = "telegram"
                route_decisions.labels(
                    route=route,
                    user_id=user_id,
                    frontend=frontend,
                    entity=entity_name
                ).inc()

                execution_time = execution_details.get("execution_time", 0)
                if execution_time > 0:
                    llm_processing_time.labels(
                        route=route,
                        approach=approach,
                        frontend=frontend,
                        entity=entity_name
                    ).observe(execution_time)

                # Count memory operations
                if execution_details.get("memories_used", 0) > 0:
                    memory_operations.labels(
                        operation_type="retrieval",
                        user_id=user_id,
                        frontend=frontend,
                        entity=entity_name
                    ).inc()
                if execution_details.get("user_profile_used", False):
                    memory_operations.labels(
                        operation_type="profile_access",
                        user_id=user_id,
                        frontend=frontend,
                        entity=entity_name
                    ).inc()

            # Send response with entity indicator
            response_text = f"🤖 **{entity_name.capitalize()}**: {answer}"

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=response_text,
                parse_mode=None  # Plain text to avoid markdown issues
            )

            # Add assistant response to conversation history
            self._add_to_conversation(user_id, "assistant", answer)

            # Mark task as done and reset timeout on success
            queue.task_done()
            self._reset_timeout(user_id)

            # Track successful request
            telegram_requests.labels(status="success", user_id=user_id, entity=entity_name).inc()

            # Log processing metrics
            logger.info(f"Telegram request processed: user={user_id}, entity={entity_name}, route={route}, latency={processing_time:.2f}s")

        except Exception as e:
            logger.error(f"Error processing message for user {user_id}: {e}")

            # Track error
            entity_name = self.get_chat_entity(str(update.effective_chat.id))
            telegram_requests.labels(status="error", user_id=user_id, entity=entity_name).inc()
            route_decisions.labels(route="error", user_id=user_id, frontend="telegram", entity=entity_name).inc()

            error_msg = f"⚠️ Произошла ошибка при обработке сообщения / Error processing message: {str(e)[:200]}..."
            await update.message.reply_text(error_msg)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        chat_id = str(update.effective_chat.id)
        current_entity = self.get_chat_entity(chat_id)

        welcome_msg = f"""👋 Привет! Я универсальный бот Prometheus.

🤖 Активная сущность: **{current_entity.capitalize()}**

Доступные команды:
• /use <entity> - переключить сущность
• /entities - список доступных сущностей
• /status - статус системы
• /help - справка

Просто напишите сообщение для общения! 🚀

Hello! I'm the universal Prometheus bot.

🤖 Active entity: **{current_entity.capitalize()}**

Available commands:
• /use <entity> - switch entity
• /entities - list available entities
• /status - system status
• /help - help

Just send a message to chat! 🤖"""

        await update.message.reply_text(welcome_msg)

    async def use_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /use command to switch entities."""
        if not context.args:
            chat_id = str(update.effective_chat.id)
            current_entity = self.get_chat_entity(chat_id)
            available = get_running_agents()

            await update.message.reply_text(
                f"🤖 Текущая сущность: **{current_entity}**\n"
                f"📋 Доступные: {', '.join(available)}\n\n"
                f"Использование: /use <entity>\n"
                f"Current entity: **{current_entity}**\n"
                f"Available: {', '.join(available)}"
            )
            return

        entity_name = context.args[0].lower()
        chat_id = str(update.effective_chat.id)

        # Check if entity exists
        if entity_name not in get_running_agents():
            try:
                # Try to initialize entity
                await get_agent(entity_name)
            except ImportError:
                await update.message.reply_text(
                    f"❌ Сущность '{entity_name}' не найдена!\n"
                    f"Доступные: {', '.join(get_running_agents())}\n\n"
                    f"Entity '{entity_name}' not found!\n"
                    f"Available: {', '.join(get_running_agents())}"
                )
                return

        # Switch entity for this chat
        self.set_chat_entity(chat_id, entity_name)

        await update.message.reply_text(
            f"✅ Переключено на сущность: **{entity_name.capitalize()}**\n"
            f"Switched to entity: **{entity_name.capitalize()}**"
        )

    async def entities_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /entities command."""
        running = get_running_agents()
        chat_id = str(update.effective_chat.id)
        current = self.get_chat_entity(chat_id)

        entities_list = []
        for entity in running:
            marker = "🟢" if entity == current else "⚪"
            entities_list.append(f"{marker} {entity.capitalize()}")

        await update.message.reply_text(
            "🤖 Доступные сущности / Available entities:\n\n" +
            "\n".join(entities_list) +
            "\n\n💬 Используйте /use <entity> для переключения"
            "\nUse /use <entity> to switch"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_msg = """🤖 Команды бота Prometheus / Prometheus Bot Commands:

/start - Начать работу / Start conversation
/use <entity> - Переключить сущность / Switch entity
/entities - Список сущностей / List entities
/status - Статус системы / System status
/help - Показать справку / Show this help

Просто отправьте сообщение для общения!
Just send a message to chat!"""

        await update.message.reply_text(help_msg)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        from core.runtime.lifecycle import system_health_check

        try:
            health_report = await system_health_check()
            running_agents = health_report["running_agents"]

            chat_id = str(update.effective_chat.id)
            current_entity = self.get_chat_entity(chat_id)

            # Calculate total timeouts
            active_timeouts = sum(1 for timeout in self.user_timeouts.values() if timeout > 0)

            status_msg = f"""📊 Статус системы Prometheus / Prometheus System Status:

🟢 Общий статус: {health_report["overall_status"]} / Overall: {health_report["overall_status"]}
🤖 Активных агентов: {len(running_agents)} / Active agents: {len(running_agents)}
📋 Агенты: {', '.join(running_agents)}
💬 Текущая сущность: **{current_entity}**
👥 Активных пользователей: {len(self.user_queues)}
⏱️ Ограниченных пользователей: {active_timeouts}"""

            await update.message.reply_text(status_msg)

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка получения статуса / Error getting status: {e!s}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages with multi-entity support."""
        try:
            # Extract user information
            uid = str(update.effective_user.id)
            text = update.message.text

            if not text:
                await update.message.reply_text("⚠️ Пожалуйста, отправьте текстовое сообщение / Please send a text message")
                return

            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

            # Process with exponential back-pressure rate limiting
            await self._rate_limited_process(uid, text, update, context)

        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            error_msg = f"⚠️ Произошла ошибка / Error: {str(e)[:100]}..."
            await update.message.reply_text(error_msg)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        logger.error(f"Update {update} caused error {context.error}")

    def setup_handlers(self):
        """Setup message and command handlers."""
        if not self.application:
            return

        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("use", self.use_command))
        self.application.add_handler(CommandHandler("entities", self.entities_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))

        # Message handler for text messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Error handler
        self.application.add_error_handler(self.error_handler)

    async def start_polling(self):
        """Start the bot polling loop."""
        # Create application without persistence (use registry memory system)
        self.application = Application.builder().token(self.token).persistence(None).build()

        # Setup handlers
        self.setup_handlers()

        # Add shutdown handler
        await add_shutdown_handler("telegram_bot", self.shutdown)

        # Start polling
        logger.info("🤖 Starting universal Telegram bot polling...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

        logger.info("✅ Universal Telegram bot is running with multi-entity support!")

        # Keep the bot running
        try:
            # Simple infinite loop that can be interrupted
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            # Cleanup
            await self.shutdown()

    async def shutdown(self):
        """Shutdown the bot gracefully."""
        if self.application:
            logger.info("🛑 Shutting down universal Telegram bot...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("✅ Universal Telegram bot shutdown complete")


class EntitySpecificTelegramBot:
    """Entity-specific Telegram bot for dedicated entity instances."""

    def __init__(self, token: str, entity_name: str):
        """Initialize entity-specific Telegram bot."""
        self.token = token
        self.entity_name = entity_name
        self.application: Application | None = None

        # Enhanced rate limiting with exponential back-pressure
        self.user_queues = {}
        self.user_timeouts = {}  # Track timeout periods per user
        self.max_queue_size = 2  # Max 2 pending requests per user
        self.base_timeout = 5    # Base timeout in seconds
        self.max_timeout = 300   # Max timeout (5 minutes)

        # Track conversation history for proper context detection
        self.user_conversations: dict[str, list] = {}
        self.max_context_messages = 3  # Keep last 3 exchanges for context

        logger.info(f"🤖 Created entity-specific bot for: {entity_name}")

    def _get_conversation_context(self, user_id: str) -> str:
        """Get formatted conversation context for the user."""
        if user_id not in self.user_conversations:
            return ""
        
        conversations = self.user_conversations[user_id]
        if not conversations:
            return ""
        
        # Format recent conversation history with markers for detection
        context_lines = []
        for entry in conversations[-self.max_context_messages:]:
            if entry["role"] == "user":
                context_lines.append(f"👤 User: {entry['content']}")
            else:
                context_lines.append(f"🤖 Assistant: {entry['content']}")
        
        return "\n".join(context_lines)

    def _add_to_conversation(self, user_id: str, role: str, content: str):
        """Add message to conversation history."""
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = []
        
        self.user_conversations[user_id].append({
            "role": role,
            "content": content[:200]  # Truncate for memory efficiency
        })
        
        # Keep only recent messages
        if len(self.user_conversations[user_id]) > self.max_context_messages * 2:
            self.user_conversations[user_id] = self.user_conversations[user_id][-self.max_context_messages * 2:]

    async def _get_user_queue(self, user_id: str) -> asyncio.Queue:
        """Get or create rate limiting queue for user."""
        if user_id not in self.user_queues:
            self.user_queues[user_id] = asyncio.Queue(maxsize=self.max_queue_size)
            self.user_timeouts[user_id] = 0
        return self.user_queues[user_id]

    def _calculate_timeout(self, user_id: str) -> float:
        """Calculate exponential back-pressure timeout."""
        current_timeout = self.user_timeouts.get(user_id, 0)
        if current_timeout == 0:
            new_timeout = self.base_timeout
        else:
            new_timeout = min(current_timeout * 2, self.max_timeout)

        self.user_timeouts[user_id] = new_timeout
        return new_timeout

    def _reset_timeout(self, user_id: str):
        """Reset timeout after successful processing."""
        self.user_timeouts[user_id] = 0

    async def _rate_limited_process(self, user_id: str, text: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process message with rate limiting for fixed entity."""
        try:
            queue = await self._get_user_queue(user_id)

            # Try to add to queue (non-blocking)
            try:
                queue.put_nowait((text, update, context, time.time()))
            except asyncio.QueueFull:
                # Calculate exponential timeout
                timeout = self._calculate_timeout(user_id)

                await update.message.reply_text(
                    f"🚫 Слишком много запросов! Попробуйте через {timeout:.0f} секунд.\n"
                    f"🚫 Too many requests! Please try again in {timeout:.0f} seconds."
                )

                # Track rate limit hit
                telegram_requests.labels(status="rate_limited", user_id=user_id, entity=self.entity_name).inc()
                return

            # Process from queue
            text, update, context, request_time = await queue.get()
            processing_start = time.time()

            # Get conversation context for continuation detection
            conversation_context = self._get_conversation_context(user_id)
            
            # Add current user message to conversation history
            self._add_to_conversation(user_id, "user", text)

            # Get agent instance from registry (fixed entity)
            try:
                agent = await get_agent(self.entity_name)
            except ImportError:
                await update.message.reply_text(
                    f"❌ Entity '{self.entity_name}' not found!\n"
                    f"Available entities: {', '.join(get_running_agents())}"
                )
                return

            # Process message with conversation context
            response = await agent.think(text, user_id=user_id, context=conversation_context)

            # Calculate processing time
            processing_time = time.time() - processing_start

            # Extract answer and metrics
            answer = str(response)
            route = "unknown"
            approach = "unknown"

            if isinstance(response, dict):
                if "result" in response:
                    answer = response["result"]

                execution_details = response.get("execution_details", {})
                route = execution_details.get("route_used", "unknown")
                approach = execution_details.get("approach", "unknown")

                # Update Prometheus metrics with entity label
                frontend = "telegram"
                route_decisions.labels(
                    route=route,
                    user_id=user_id,
                    frontend=frontend,
                    entity=self.entity_name
                ).inc()

                execution_time = execution_details.get("execution_time", 0)
                if execution_time > 0:
                    llm_processing_time.labels(
                        route=route,
                        approach=approach,
                        frontend=frontend,
                        entity=self.entity_name
                    ).observe(execution_time)

                # Count memory operations
                if execution_details.get("memories_used", 0) > 0:
                    memory_operations.labels(
                        operation_type="retrieval",
                        user_id=user_id,
                        frontend=frontend,
                        entity=self.entity_name
                    ).inc()
                if execution_details.get("user_profile_used", False):
                    memory_operations.labels(
                        operation_type="profile_access",
                        user_id=user_id,
                        frontend=frontend,
                        entity=self.entity_name
                    ).inc()

            # Send response (no entity indicator since it's dedicated)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=answer,
                parse_mode=None  # Plain text to avoid markdown issues
            )
            
            # Add assistant response to conversation history
            self._add_to_conversation(user_id, "assistant", answer)

            # Mark task as done and reset timeout on success
            queue.task_done()
            self._reset_timeout(user_id)

            # Track successful request
            telegram_requests.labels(status="success", user_id=user_id, entity=self.entity_name).inc()

            # Log processing metrics
            logger.info(f"Entity-specific Telegram request: user={user_id}, entity={self.entity_name}, route={route}, latency={processing_time:.2f}s")

        except Exception as e:
            logger.error(f"Error processing message for user {user_id} on entity {self.entity_name}: {e}")

            # Track error
            telegram_requests.labels(status="error", user_id=user_id, entity=self.entity_name).inc()
            route_decisions.labels(route="error", user_id=user_id, frontend="telegram", entity=self.entity_name).inc()

            error_msg = f"⚠️ Произошла ошибка при обработке сообщения / Error processing message: {str(e)[:200]}..."
            await update.message.reply_text(error_msg)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command for entity-specific bot."""
        # Get entity info for personalized greeting
        try:
            agent = await get_agent(self.entity_name)
            entity_info = getattr(agent, 'identity_config', {})
            entity_display_name = entity_info.get('name', self.entity_name.capitalize())
            personality = entity_info.get('personality', {}).get('summary', 'AI Assistant')
        except:
            entity_display_name = self.entity_name.capitalize()
            personality = 'AI Assistant'

        welcome_msg = f"""👋 Привет! Я {entity_display_name}.

🤖 {personality}

Доступные команды:
• /status - статус системы
• /help - справка

Просто напишите сообщение для общения! 🚀

Hello! I'm {entity_display_name}.

🤖 {personality}

Available commands:
• /status - system status
• /help - help

Just send a message to chat! 🚀"""

        await update.message.reply_text(welcome_msg)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command for entity-specific bot."""
        help_msg = f"""🤖 {self.entity_name.capitalize()} Bot Commands:

/start - Начать работу / Start conversation
/status - Статус системы / System status
/help - Показать справку / Show this help

Просто отправьте сообщение для общения!
Just send a message to chat!

🎯 Этот бот всегда отвечает как {self.entity_name.capitalize()}
This bot always responds as {self.entity_name.capitalize()}"""

        await update.message.reply_text(help_msg)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command for entity-specific bot."""
        from core.runtime.lifecycle import system_health_check

        try:
            health_report = await system_health_check()
            
            # Calculate total timeouts
            active_timeouts = sum(1 for timeout in self.user_timeouts.values() if timeout > 0)

            status_msg = f"""📊 Статус бота {self.entity_name.capitalize()} / {self.entity_name.capitalize()} Bot Status:

🟢 Общий статус: {health_report["overall_status"]} / Overall: {health_report["overall_status"]}
🤖 Сущность: **{self.entity_name}** / Entity: **{self.entity_name}**
👥 Активных пользователей: {len(self.user_queues)}
⏱️ Ограниченных пользователей: {active_timeouts}"""

            await update.message.reply_text(status_msg)

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка получения статуса / Error getting status: {e!s}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages for entity-specific bot."""
        try:
            # Extract user information
            uid = str(update.effective_user.id)
            text = update.message.text

            if not text:
                await update.message.reply_text("⚠️ Пожалуйста, отправьте текстовое сообщение / Please send a text message")
                return

            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

            # Process with exponential back-pressure rate limiting
            await self._rate_limited_process(uid, text, update, context)

        except Exception as e:
            logger.error(f"Error in entity-specific message handler: {e}")
            error_msg = f"⚠️ Произошла ошибка / Error: {str(e)[:100]}..."
            await update.message.reply_text(error_msg)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        logger.error(f"Update {update} caused error {context.error}")

    def setup_handlers(self):
        """Setup message and command handlers for entity-specific bot."""
        if not self.application:
            return

        # Command handlers (simplified for entity-specific bot)
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))

        # Message handler for text messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Error handler
        self.application.add_error_handler(self.error_handler)

    async def start_polling(self):
        """Start the entity-specific bot polling loop."""
        # Create application without persistence (use registry memory system)
        self.application = Application.builder().token(self.token).persistence(None).build()

        # Setup handlers
        self.setup_handlers()

        # Add shutdown handler
        await add_shutdown_handler(f"telegram_bot_{self.entity_name}", self.shutdown)

        # Start polling
        logger.info(f"🤖 Starting entity-specific Telegram bot for {self.entity_name}...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

        logger.info(f"✅ Entity-specific Telegram bot for {self.entity_name} is running!")

        # Keep the bot running
        try:
            # Simple infinite loop that can be interrupted
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            # Cleanup
            await self.shutdown()

    async def shutdown(self):
        """Shutdown the entity-specific bot gracefully."""
        if self.application:
            logger.info(f"🛑 Shutting down entity-specific Telegram bot for {self.entity_name}...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info(f"✅ Entity-specific Telegram bot for {self.entity_name} shutdown complete")


async def create_entity_bot(token: str, entity_name: str):
    """Create and run entity-specific bot."""
    bot = EntitySpecificTelegramBot(token, entity_name)
    
    try:
        await bot.start_polling()
    except KeyboardInterrupt:
        logger.info(f"🛑 Entity-specific bot for {entity_name} stopped by user")
    except Exception as e:
        logger.error(f"❌ Entity-specific bot for {entity_name} error: {e}")


async def main():
    """Main entry point for Telegram bot."""
    # Get bot token from environment
    bot_token = os.getenv("TELEGRAM_TOKEN")

    if not bot_token:
        logger.error("❌ TELEGRAM_TOKEN environment variable not set!")
        logger.error("Please set your Telegram bot token: export TELEGRAM_TOKEN=your_token_here")
        return

    # Create and start bot
    bot = UniversalTelegramBot(bot_token)

    try:
        await bot.start_polling()
    except KeyboardInterrupt:
        logger.info("🛑 Universal Telegram bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Universal Telegram bot error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
