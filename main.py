"""Bot entrypoint."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import load_settings
from app.db.database import Database
from app.handlers.bot import router as bot_router
from app.utils.daily_reporter import run_daily_report_loop
from app.utils.middlewares import DatabaseMiddleware


async def run_bot() -> None:
    settings = load_settings()
    db = Database(settings.database_url)
    await db.connect()
    await db.initialize()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    mw = DatabaseMiddleware(db=db, admin_ids=settings.admin_ids)
    dp.message.middleware(mw)
    dp.callback_query.middleware(mw)

    dp.include_router(bot_router)

    daily_task = asyncio.create_task(
        run_daily_report_loop(bot=bot, db=db, admin_ids=settings.admin_ids)
    )

    logging.info("Bot ishga tushdi")
    try:
        await dp.start_polling(bot)
    finally:
        daily_task.cancel()
        await db.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_bot())
