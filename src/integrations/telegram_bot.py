"""
ASTRAEUS - Autonomous Life Orchestrator
Telegram Bot Module

This module implements the Telegram bot interface
for user interaction and notifications.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, Awaitable
import structlog

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

from src.config import settings
from src.brain.llm_client import get_llm_client, BaseLLMClient
from src.brain.system_prompt import get_system_prompt
from src.brain.context_manager import context_manager
from src.brain.decision_engine import decision_engine
from src.location.gps_handler import gps_handler
from src.location.transit_finder import transit_finder
from src.integrations.weather_api import weather_api
from src.scheduler.time_calculator import time_calculator

logger = structlog.get_logger()


class TelegramBot:
    """
    Main Telegram bot class that handles user interactions.
    """
    
    def __init__(self):
        self.token = settings.telegram_bot_token
        self.authorized_user = settings.telegram_authorized_user_id
        self.app: Optional[Application] = None
        self.llm_client: Optional[BaseLLMClient] = None
        self.user_name = settings.user_name
        
        # Scheduled jobs
        self.scheduled_jobs: Dict[str, Any] = {}
        
        logger.info("Telegram bot initialized", authorized_user=self.authorized_user)
    
    async def initialize(self) -> None:
        """Initialize bot and LLM client."""
        self.llm_client = get_llm_client()
        logger.info("LLM client ready")
    
    def build_application(self) -> Application:
        """Build and configure the Telegram application."""
        self.app = Application.builder().token(self.token).build()
        
        # Register handlers
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("konum", self.cmd_location))
        self.app.add_handler(CommandHandler("hava", self.cmd_weather))
        self.app.add_handler(CommandHandler("plan", self.cmd_plan))
        self.app.add_handler(CommandHandler("durak", self.cmd_transit))
        self.app.add_handler(CommandHandler("sifirla", self.cmd_reset))
        
        # Location handler
        self.app.add_handler(MessageHandler(filters.LOCATION, self.handle_location))
        
        # Callback query handler for inline buttons
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # General message handler (AI chat)
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        return self.app
    
    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized to use the bot."""
        return user_id == self.authorized_user
    
    async def send_unauthorized_message(self, update: Update) -> None:
        """Send unauthorized access message."""
        await update.message.reply_text(
            "⛔ Bu bot özel kullanım içindir.\n"
            "Yetkiniz bulunmamaktadır."
        )
    
    # ==================== Command Handlers ====================
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if not self.is_authorized(update.effective_user.id):
            await self.send_unauthorized_message(update)
            return
        
        keyboard = ReplyKeyboardMarkup(
            [
                ["🌤️ Hava Durumu", "📍 Konumum"],
                ["🚌 En Yakın Durak", "📅 Bugünkü Plan"],
                ["❓ Yardım"]
            ],
            resize_keyboard=True
        )
        
        welcome_message = f"""🌟 Merhaba {self.user_name}!

Ben ASTRAEUS, senin kişisel yaşam asistanınım. 🤖

📋 **Neler Yapabilirim:**
• Günlük planını optimize edebilirim
• Zamanında kalkış hatırlatması yapabilirim
• Hava durumuna göre süreleri ayarlayabilirim
• En yakın toplu taşıma duraklarını bulabilirim

💬 Benimle doğal bir şekilde konuşabilirsin!

Örnek: "Kafedeyim, bir saat sonra dersim var"

📍 Daha iyi yardım için konumunu paylaş!"""
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        if not self.is_authorized(update.effective_user.id):
            await self.send_unauthorized_message(update)
            return
        
        help_text = f"""📚 **ASTRAEUS Yardım**

**Komutlar:**
/start - Botu başlat
/konum - Konum paylaş
/hava - Hava durumu
/plan - Günlük plan
/durak - En yakın duraklar
/sifirla - Sohbeti sıfırla

**Doğal Konuşma Örnekleri:**
• "20:00'de dersim var"
• "Yarım saat sonra eve gitmeliyim"
• "Bugün ne yapmam gerekiyor?"
• "Otobüsü kaçırdım, ne yapmalıyım?"

**Konum Paylaşımı:**
📍 Telegram'dan konum paylaşarak daha akıllı öneriler alabilirsin.

**Formül:**
```
T_kalkış = T_etkinlik - (T_ulaşım + T_yürüme + T_hazırlık + T_tampon)
```

{self.user_name}, her zaman yanındayım! 💪"""
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /hava command."""
        if not self.is_authorized(update.effective_user.id):
            await self.send_unauthorized_message(update)
            return
        
        await update.message.reply_text("🌤️ Hava durumu alınıyor...")
        
        # Get user's location if available
        user_context = context_manager.get_context(update.effective_user.id)
        lat, lon = user_context.user_state.latitude, user_context.user_state.longitude
        
        if lat and lon:
            weather = await weather_api.get_current_weather(lat=lat, lon=lon)
        else:
            weather = await weather_api.get_current_weather()
        
        if weather:
            # Check for alerts
            alert = await weather_api.get_weather_alert(
                lat=lat, lon=lon
            ) if lat else await weather_api.get_weather_alert()
            
            message = weather.format_summary()
            if alert:
                message += f"\n\n{alert}"
            
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(
                "❌ Hava durumu alınamadı. Lütfen daha sonra tekrar dene."
            )
    
    async def cmd_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /konum command - request location sharing."""
        if not self.is_authorized(update.effective_user.id):
            await self.send_unauthorized_message(update)
            return
        
        keyboard = [
            [InlineKeyboardButton("📍 Konumumu Paylaş", callback_data="share_location")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📍 Konumunu paylaşmak için aşağıdaki butona bas veya "
            "Telegram'dan doğrudan konum gönder.",
            reply_markup=reply_markup
        )
    
    async def cmd_transit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /durak command - find nearby transit stops."""
        if not self.is_authorized(update.effective_user.id):
            await self.send_unauthorized_message(update)
            return
        
        user_context = context_manager.get_context(update.effective_user.id)
        lat, lon = user_context.user_state.latitude, user_context.user_state.longitude
        
        if not lat or not lon:
            await update.message.reply_text(
                "📍 Önce konumunu paylaşman gerekiyor!\n"
                "Konum paylaşmak için: /konum"
            )
            return
        
        await update.message.reply_text("🚌 Yakındaki duraklar aranıyor...")
        
        stops = await transit_finder.find_nearby_stops(lat, lon, radius_meters=500)
        
        if stops:
            message = f"📍 **Yakındaki Duraklar**\n\n"
            for i, stop in enumerate(stops[:5], 1):
                message += f"{i}. {transit_finder.format_stop_info(stop)}\n\n"
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(
                "❌ Yakınında durak bulunamadı. "
                "Arama yarıçapını genişletmek ister misin?"
            )
    
    async def cmd_plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /plan command - show today's plan."""
        if not self.is_authorized(update.effective_user.id):
            await self.send_unauthorized_message(update)
            return
        
        # For now, show a placeholder
        # In production, this would fetch from database
        await update.message.reply_text(
            f"📅 **{self.user_name}'ın Bugünkü Planı**\n\n"
            "📝 Henüz plan eklenmedi.\n\n"
            "Bana etkinliklerini söyle:\n"
            "• '20:00'de Python dersi var'\n"
            "• 'Yarın 09:00'da toplantı'\n\n"
            "veya doğrudan konuşarak plan oluşturalım! 💬",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /sifirla command - reset conversation."""
        if not self.is_authorized(update.effective_user.id):
            await self.send_unauthorized_message(update)
            return
        
        context_manager.clear_context(update.effective_user.id)
        await update.message.reply_text(
            "🔄 Sohbet sıfırlandı!\n"
            f"Merhaba {self.user_name}, yeniden başlayalım. 👋"
        )
    
    # ==================== Message Handlers ====================
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle regular text messages - main AI chat."""
        if not self.is_authorized(update.effective_user.id):
            await self.send_unauthorized_message(update)
            return
        
        user_message = update.message.text
        user_id = update.effective_user.id
        
        # Handle quick reply buttons
        if user_message == "🌤️ Hava Durumu":
            await self.cmd_weather(update, context)
            return
        elif user_message == "📍 Konumum":
            await self.cmd_location(update, context)
            return
        elif user_message == "🚌 En Yakın Durak":
            await self.cmd_transit(update, context)
            return
        elif user_message == "📅 Bugünkü Plan":
            await self.cmd_plan(update, context)
            return
        elif user_message == "❓ Yardım":
            await self.cmd_help(update, context)
            return
        
        # Get user context
        user_context = context_manager.get_context(user_id)
        user_context.add_user_message(user_message)
        
        # Send typing indicator
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        # Build context for AI
        weather_str = None
        weather = await weather_api.get_current_weather()
        if weather:
            weather_str = weather_api.format_for_prompt(weather)
        
        system_prompt = get_system_prompt(
            user_name=self.user_name,
            current_time=datetime.now(),
            current_location=user_context.user_state.current_location,
            weather_info=weather_str
        )
        
        try:
            # Generate AI response
            response = await self.llm_client.generate(
                prompt=user_message,
                system_prompt=system_prompt,
                temperature=0.7
            )
            
            user_context.add_assistant_message(response)
            
            await update.message.reply_text(
                response,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error("AI response failed", error=str(e))
            await update.message.reply_text(
                f"❌ Üzgünüm {self.user_name}, bir sorun oluştu.\n"
                "Lütfen tekrar dene."
            )
    
    async def handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle location sharing."""
        if not self.is_authorized(update.effective_user.id):
            await self.send_unauthorized_message(update)
            return
        
        location = update.message.location
        user_id = update.effective_user.id
        
        await update.message.reply_text("📍 Konum alınıyor...")
        
        # Reverse geocode to get address
        loc = await gps_handler.reverse_geocode(
            location.latitude,
            location.longitude
        )
        
        # Update user context
        user_context = context_manager.get_context(user_id)
        user_context.update_location(
            location_name=loc.address or f"{location.latitude:.4f}, {location.longitude:.4f}",
            latitude=location.latitude,
            longitude=location.longitude
        )
        
        # Find nearby transit
        stops = await transit_finder.find_nearby_stops(
            location.latitude,
            location.longitude,
            radius_meters=500
        )
        
        message = f"✅ Konum güncellendi!\n\n📍 {loc.address or 'Bilinmeyen konum'}"
        
        if stops:
            nearest = stops[0]
            message += f"\n\n🚌 En yakın durak:\n{transit_finder.format_stop_info(nearest)}"
        
        # Check weather at location
        weather = await weather_api.get_current_weather(
            lat=location.latitude,
            lon=location.longitude
        )
        if weather and weather.is_bad_weather:
            message += f"\n\n⚠️ {weather.emoji} Dikkat: {weather.description}"
        
        await update.message.reply_text(message)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline button callbacks."""
        query = update.callback_query
        await query.answer()
        
        if query.data == "share_location":
            await query.message.reply_text(
                "📍 Konumunu paylaşmak için:\n"
                "1. Mesaj alanının yanındaki 📎 (ataş) ikonuna tıkla\n"
                "2. 'Konum' seçeneğini seç\n"
                "3. Mevcut konumunu gönder"
            )
    
    # ==================== Scheduled Notifications ====================
    
    async def schedule_reminder(
        self,
        user_id: int,
        message: str,
        trigger_time: datetime,
        job_id: str = None
    ) -> str:
        """Schedule a reminder notification."""
        if not self.app or not self.app.job_queue:
            logger.error("Job queue not available")
            return None
        
        job_id = job_id or f"reminder_{datetime.now().timestamp()}"
        delay = (trigger_time - datetime.now()).total_seconds()
        
        if delay < 0:
            logger.warning("Cannot schedule reminder in the past")
            return None
        
        self.app.job_queue.run_once(
            lambda ctx: self._send_reminder(ctx, user_id, message),
            when=delay,
            name=job_id
        )
        
        self.scheduled_jobs[job_id] = {
            "user_id": user_id,
            "message": message,
            "trigger_time": trigger_time
        }
        
        logger.info("Reminder scheduled", job_id=job_id, trigger=trigger_time.isoformat())
        return job_id
    
    async def _send_reminder(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        message: str
    ) -> None:
        """Send a scheduled reminder."""
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info("Reminder sent", user_id=user_id)
        except Exception as e:
            logger.error("Failed to send reminder", error=str(e))
    
    # ==================== Bot Lifecycle ====================
    
    async def run(self) -> None:
        """Run the bot."""
        await self.initialize()
        app = self.build_application()
        
        logger.info("Starting Telegram bot...")
        
        if settings.environment == "production" and settings.webhook_url:
            # Webhook mode for production
            await app.run_webhook(
                listen="0.0.0.0",
                port=settings.webhook_port,
                url_path=self.token,
                webhook_url=f"{settings.webhook_url}/{self.token}"
            )
        else:
            # Polling mode for development
            await app.run_polling(drop_pending_updates=True)


# Create bot instance
telegram_bot = TelegramBot()
