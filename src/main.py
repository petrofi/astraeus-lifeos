"""
ASTRAEUS - Autonomous Life Orchestrator
Main Entry Point

This is the main application that orchestrates all modules
and runs the Telegram bot.
"""

import asyncio
import signal
import sys
from datetime import datetime
import structlog

from src.config import settings
from src.database.repository import database
from src.integrations.telegram_bot import telegram_bot

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer(colors=True)
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def startup() -> None:
    """Initialize all services on startup."""
    logger.info("=" * 50)
    logger.info("ASTRAEUS - Autonomous Life Orchestrator")
    logger.info("=" * 50)
    logger.info(f"Starting up at {datetime.now().isoformat()}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"AI Provider: {settings.ai_provider}")
    logger.info(f"User: {settings.user_name}")
    logger.info("=" * 50)
    
    # Connect to database
    try:
        await database.connect()
        await database.create_tables()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error("❌ Database connection failed", error=str(e))
        logger.warning("Continuing without database persistence...")
    
    # Initialize Telegram bot
    await telegram_bot.initialize()
    logger.info("✅ Telegram bot initialized")


async def shutdown() -> None:
    """Cleanup on shutdown."""
    logger.info("Shutting down...")
    
    # Disconnect database
    await database.disconnect()
    
    logger.info("Goodbye! 👋")


async def main() -> None:
    """Main application entry point."""
    try:
        # Startup
        await startup()
        
        # Run the bot
        await telegram_bot.run()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Application error", error=str(e))
        raise
    finally:
        await shutdown()


def handle_signal(signum, frame):
    """Handle termination signals."""
    logger.info(f"Received signal {signum}")
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Run the application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
