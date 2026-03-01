"""Application entry point for PrintShop Micro-CRM Telegram Bot."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import load_settings
from app.db.database import Database
from app.handlers.bot import router as bot_router
from app.utils.middlewares import DatabaseMiddleware


async def run_bot() -> None:
    """Create bot objects, register routes, and start polling."""

    settings = load_settings()
    db = Database(settings.db_path)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()

    # Make database instance available in all message and callback handlers.
    database_middleware = DatabaseMiddleware(db=db, admin_ids=settings.admin_ids or set())
    dispatcher.message.middleware(database_middleware)
    dispatcher.callback_query.middleware(database_middleware)

    dispatcher.include_router(bot_router)

    logging.info("Bot is starting polling...")
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_bot())
