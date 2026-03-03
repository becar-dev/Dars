"""Application configuration loading utilities."""

from dataclasses import dataclass
import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    bot_token: str
    database_url: str
    admin_ids: set[int]
    tz: ZoneInfo


def _parse_admin_ids(value: str) -> set[int]:
    result: set[int] = set()
    for token in value.split(","):
        token = token.strip()
        if token.isdigit():
            result.add(int(token))
    return result


def load_settings() -> Settings:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError("BOT_TOKEN .env ichida kiritilmagan")

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("DATABASE_URL .env ichida kiritilmagan")

    tz_name = os.getenv("TZ", "Asia/Tashkent").strip() or "Asia/Tashkent"
    return Settings(
        bot_token=bot_token,
        database_url=database_url,
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        tz=ZoneInfo(tz_name),
    )
