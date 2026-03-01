"""Application configuration loading utilities."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    bot_token: str
    db_path: str = "crm.db"
    admin_ids: set[int] | None = None


def _parse_admin_ids(value: str) -> set[int]:
    """Parse ADMIN_IDS=1,2,3 environment variable into int set."""

    result: set[int] = set()
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        if token.isdigit():
            result.add(int(token))
    return result


def load_settings() -> Settings:
    """Load configuration from .env and validate required values."""

    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("BOT_TOKEN is not set. Add it to your .env file.")

    db_path = os.getenv("DB_PATH", "crm.db").strip() or "crm.db"
    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
    return Settings(bot_token=token, db_path=db_path, admin_ids=admin_ids)
