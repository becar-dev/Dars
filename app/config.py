"""Application configuration loading utilities."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    bot_token: str
    db_path: str = "crm.db"



def load_settings() -> Settings:
    """Load configuration from .env and validate required values."""

    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("BOT_TOKEN is not set. Add it to your .env file.")
    return Settings(bot_token=token)
