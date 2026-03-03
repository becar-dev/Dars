"""Custom aiogram middlewares."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware

from app.db.database import Database


class DatabaseMiddleware(BaseMiddleware):
    """Inject shared runtime objects into handler data."""

    def __init__(self, db: Database, admin_ids: set[int] | None = None) -> None:
        self.db = db
        self.admin_ids = admin_ids or set()

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        data["db"] = self.db
        data["admin_ids"] = self.admin_ids
        return await handler(event, data)
