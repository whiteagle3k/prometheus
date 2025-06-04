"""
Telegram Bot for Aletheia Service

Provides Telegram interface for interacting with Aletheia.
Uses singleton service to share instance with other frontends.
"""

import os
import asyncio
import logging
from typing import Optional

from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

from .singleton import get_agent, is_service_running


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class AletheiaTelegramBot:
    """Telegram bot interface for Aletheia."""
    
    def __init__(self, token: str):
        """Initialize the Telegram bot."""
        self.token = token
        self.application: Optional[Application] = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_msg = """👋 Привет! Я Алетейя, автономный ИИ-агент.

Я могу помочь с:
• Техническими вопросами и объяснениями
• Исследованием сложных тем
• Анализом и рассуждениями
• Обучением и развитием

Просто напишите мне сообщение, и я отвечу! 🚀

Hello! I'm Aletheia, an autonomous AI agent ready to help with technical questions, research, analysis, and learning. Just send me a message! 🤖"""
        
        await update.message.reply_text(welcome_msg)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_msg = """🤖 Команды Алетейи / Aletheia Commands:

/start - Начать работу / Start conversation
/help - Показать справку / Show this help
/status - Статус системы / System status

Просто отправьте сообщение для общения!
Just send a message to chat!"""
        
        await update.message.reply_text(help_msg)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        running = is_service_running()
        status_msg = f"""📊 Статус Алетейи / Aletheia Status:

🟢 Сервис: {'Активен' if running else 'Инициализируется'} / {'Running' if running else 'Initializing'}
🧠 Режим: Автономный ИИ-агент / Autonomous AI Agent
⚡ Маршрутизация: Оптимизированная / Optimized Routing"""
        
        await update.message.reply_text(status_msg)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages."""
        try:
            # Extract user information
            uid = str(update.effective_user.id)
            text = update.message.text
            
            if not text:
                await update.message.reply_text("⚠️ Пожалуйста, отправьте текстовое сообщение / Please send a text message")
                return
            
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Get agent and process message
            agent = await get_agent()
            response = await agent.think(text, user_id=uid)
            
            # Extract answer text
            answer = str(response)
            if isinstance(response, dict) and 'result' in response:
                answer = response['result']
            
            # Send response
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=answer,
                parse_mode=None  # Plain text to avoid markdown issues
            )
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_msg = f"⚠️ Произошла ошибка при обработке сообщения / Error processing message: {str(e)[:200]}..."
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
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Message handler for text messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    async def start_polling(self):
        """Start the bot polling loop."""
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        # Setup handlers
        self.setup_handlers()
        
        # Start polling
        logger.info("🤖 Starting Telegram bot polling...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("✅ Telegram bot is running!")
        
        # Keep the bot running
        try:
            # Run until interrupted
            await self.application.updater.idle()
        finally:
            # Cleanup
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()


async def main():
    """Main entry point for Telegram bot."""
    # Get bot token from environment
    bot_token = os.getenv('TELEGRAM_TOKEN')
    
    if not bot_token:
        logger.error("❌ TELEGRAM_TOKEN environment variable not set!")
        logger.error("Please set your Telegram bot token: export TELEGRAM_TOKEN=your_token_here")
        return
    
    # Create and start bot
    bot = AletheiaTelegramBot(bot_token)
    
    try:
        await bot.start_polling()
    except KeyboardInterrupt:
        logger.info("🛑 Telegram bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Telegram bot error: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 