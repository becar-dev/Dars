"""Kunlik hisobot yuboruvchi fon vazifa."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.db.database import Database


@dataclass(slots=True)
class DailyReportConfig:
    hour: int = 21
    minute: int = 0
    tz_name: str = "Asia/Tashkent"


def seconds_until_next_run(config: DailyReportConfig, now: datetime | None = None) -> float:
    tz = ZoneInfo(config.tz_name)
    current = now.astimezone(tz) if now else datetime.now(tz)
    target = current.replace(hour=config.hour, minute=config.minute, second=0, microsecond=0)
    if current >= target:
        target = target + timedelta(days=1)
    return max((target - current).total_seconds(), 0.0)


def _escape_md(text: str) -> str:
    chars = r"_[]()~`>#+-=|{}.!"
    for c in chars:
        text = text.replace(c, f"\\{c}")
    return text


async def run_daily_report_loop(
    bot: Bot,
    db: Database,
    admin_ids: set[int] | None,
    config: DailyReportConfig | None = None,
) -> None:
    cfg = config or DailyReportConfig()
    admins = admin_ids or set()

    while True:
        await asyncio.sleep(seconds_until_next_run(cfg))
        if not admins:
            logging.warning("ADMIN_IDS bo‘sh, kunlik hisobot yuborilmadi")
            continue

        try:
            summary = await db.get_today_summary()
            top = await db.get_top_items_today(limit=3)
        except Exception as exc:
            logging.exception("Kunlik hisobot uchun DB xatolik: %s", exc)
            summary = {"revenue": 0, "orders_count": 0, "items_count": 0, "asked_price_count": 0}
            top = []

        sana = datetime.now(ZoneInfo(cfg.tz_name)).date().isoformat()
        lines = [
            "📌 *Bugungi hisobot*",
            f"🗓 Sana: `{sana}`",
            f"💰 Tushum: *{summary['revenue']}* so'm",
            f"🧾 Buyurtmalar: *{summary['orders_count']}* ta",
            f"📦 Itemlar: *{summary['items_count']}* ta",
            f"❓ Faqat narx so‘radi: *{summary['asked_price_count']}* ta",
            "🏆 Top 3 xizmat/mahsulot:",
        ]

        if top:
            for idx, item in enumerate(top, start=1):
                lines.append(f"{idx}) {_escape_md(item['item_name'])} — *{item['count']}* ta")
        else:
            lines.extend(["1) - — *0* ta", "2) - — *0* ta", "3) - — *0* ta"])

        text = "\n".join(lines)

        for admin_id in admins:
            try:
                await bot.send_message(admin_id, text, parse_mode=ParseMode.MARKDOWN_V2)
            except (TelegramBadRequest, TelegramForbiddenError) as exc:
                logging.warning("Hisobot yuborilmadi admin=%s: %s", admin_id, exc)
            except Exception as exc:  # pragma: no cover
                logging.exception("Kutilmagan xatolik admin=%s: %s", admin_id, exc)
