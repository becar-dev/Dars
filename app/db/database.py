"""PostgreSQL async access layer for mini-CRM."""

from __future__ import annotations

import logging
from typing import Any

import asyncpg


class Database:
    """Async PostgreSQL wrapper based on connection pool."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(dsn=self.dsn, min_size=1, max_size=10)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()

    def _pool(self) -> asyncpg.Pool:
        if self.pool is None:
            raise RuntimeError("Database pool initialized emas")
        return self.pool

    async def initialize(self) -> None:
        """Create tables/indexes if missing."""

        sql = """
        CREATE TABLE IF NOT EXISTS orders (
            id BIGSERIAL PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by BIGINT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('asked_price','ordered','urgent','returned')),
            total_amount BIGINT NOT NULL DEFAULT 0 CHECK (total_amount >= 0)
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id BIGSERIAL PRIMARY KEY,
            order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            category TEXT NOT NULL CHECK (category IN ('service','stationery')),
            item_name TEXT NOT NULL,
            model_name TEXT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            unit_price BIGINT NOT NULL CHECK (unit_price >= 0),
            line_total BIGINT NOT NULL CHECK (line_total >= 0)
        );

        CREATE TABLE IF NOT EXISTS catalog_services (
            id BIGSERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        );

        CREATE TABLE IF NOT EXISTS catalog_products (
            id BIGSERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        );

        CREATE TABLE IF NOT EXISTS catalog_product_models (
            id BIGSERIAL PRIMARY KEY,
            product_id BIGINT NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
            model_name TEXT NOT NULL,
            unit_price BIGINT NOT NULL CHECK (unit_price >= 0),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            UNIQUE(product_id, model_name)
        );

        CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
        CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
        CREATE INDEX IF NOT EXISTS idx_order_items_item_model ON order_items(item_name, model_name);
        """
        async with self._pool().acquire() as conn:
            await conn.execute(sql)
            await self._seed_defaults(conn)

    async def _seed_defaults(self, conn: asyncpg.Connection) -> None:
        for name in ["Nusxa", "Kitob", "Chop", "Dizayn"]:
            await conn.execute(
                "INSERT INTO catalog_services(name,is_active) VALUES($1,TRUE) ON CONFLICT (name) DO NOTHING",
                name,
            )
        for name in ["Ruchka", "Daftar", "Marker"]:
            await conn.execute(
                "INSERT INTO catalog_products(name,is_active) VALUES($1,TRUE) ON CONFLICT (name) DO NOTHING",
                name,
            )

    async def get_services(self) -> list[dict[str, Any]]:
        async with self._pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, name FROM catalog_services WHERE is_active=TRUE ORDER BY name"
            )
        return [dict(r) for r in rows]

    async def get_products(self) -> list[dict[str, Any]]:
        async with self._pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, name FROM catalog_products WHERE is_active=TRUE ORDER BY name"
            )
        return [dict(r) for r in rows]

    async def get_models_by_product(self, product_id: int) -> list[dict[str, Any]]:
        async with self._pool().acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, model_name, unit_price
                FROM catalog_product_models
                WHERE product_id=$1 AND is_active=TRUE
                ORDER BY model_name
                """,
                product_id,
            )
        return [dict(r) for r in rows]

    async def admin_add_product(self, name: str) -> None:
        async with self._pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO catalog_products(name,is_active) VALUES($1,TRUE) ON CONFLICT (name) DO NOTHING",
                name,
            )

    async def admin_edit_product(self, product_id: int, name: str, is_active: bool) -> None:
        async with self._pool().acquire() as conn:
            await conn.execute(
                "UPDATE catalog_products SET name=$1, is_active=$2 WHERE id=$3",
                name,
                is_active,
                product_id,
            )

    async def admin_soft_delete_product(self, product_id: int) -> None:
        async with self._pool().acquire() as conn:
            await conn.execute("UPDATE catalog_products SET is_active=FALSE WHERE id=$1", product_id)

    async def admin_add_model(self, product_id: int, model_name: str, unit_price: int) -> None:
        async with self._pool().acquire() as conn:
            await conn.execute(
                """
                INSERT INTO catalog_product_models(product_id, model_name, unit_price, is_active)
                VALUES($1,$2,$3,TRUE)
                ON CONFLICT (product_id, model_name)
                DO UPDATE SET unit_price=EXCLUDED.unit_price, is_active=TRUE
                """,
                product_id,
                model_name,
                unit_price,
            )

    async def admin_edit_model(self, model_id: int, model_name: str, unit_price: int, is_active: bool) -> None:
        async with self._pool().acquire() as conn:
            await conn.execute(
                "UPDATE catalog_product_models SET model_name=$1, unit_price=$2, is_active=$3 WHERE id=$4",
                model_name,
                unit_price,
                is_active,
                model_id,
            )

    async def admin_soft_delete_model(self, model_id: int) -> None:
        async with self._pool().acquire() as conn:
            await conn.execute("UPDATE catalog_product_models SET is_active=FALSE WHERE id=$1", model_id)

    async def create_order(self, created_by: int, status: str, items: list[dict[str, Any]]) -> int:
        total_amount = sum(int(i["line_total"]) for i in items)
        async with self._pool().acquire() as conn:
            async with conn.transaction():
                order_id = await conn.fetchval(
                    "INSERT INTO orders(created_by,status,total_amount) VALUES($1,$2,$3) RETURNING id",
                    created_by,
                    status,
                    total_amount,
                )
                for item in items:
                    await conn.execute(
                        """
                        INSERT INTO order_items(order_id, category, item_name, model_name, quantity, unit_price, line_total)
                        VALUES($1,$2,$3,$4,$5,$6,$7)
                        """,
                        order_id,
                        item["category"],
                        item["item_name"],
                        item.get("model_name"),
                        int(item["quantity"]),
                        int(item["unit_price"]),
                        int(item["line_total"]),
                    )
        return int(order_id)

    async def get_period_summary(self, days: int | None = None) -> dict[str, Any]:
        where = ""
        params: list[Any] = []
        if days is not None:
            where = "WHERE (created_at AT TIME ZONE 'Asia/Tashkent')::date >= ((now() AT TIME ZONE 'Asia/Tashkent')::date - $1::int + 1)"
            params = [days]

        async with self._pool().acquire() as conn:
            row = await conn.fetchrow(
                f"""
                SELECT
                    COUNT(*)::bigint AS orders_count,
                    COALESCE(SUM(total_amount), 0)::bigint AS revenue,
                    COALESCE(SUM(CASE WHEN status='asked_price' THEN 1 ELSE 0 END), 0)::bigint AS asked_price_count
                FROM orders
                {where}
                """,
                *params,
            )

            item_where = ""
            item_params: list[Any] = []
            if days is not None:
                item_where = "WHERE (o.created_at AT TIME ZONE 'Asia/Tashkent')::date >= ((now() AT TIME ZONE 'Asia/Tashkent')::date - $1::int + 1)"
                item_params = [days]

            items_count = await conn.fetchval(
                f"""
                SELECT COUNT(*)::bigint
                FROM order_items oi
                JOIN orders o ON o.id=oi.order_id
                {item_where}
                """,
                *item_params,
            )

            top = await conn.fetch(
                f"""
                SELECT
                    oi.item_name,
                    oi.model_name,
                    COUNT(*)::bigint AS cnt
                FROM order_items oi
                JOIN orders o ON o.id=oi.order_id
                {item_where}
                GROUP BY oi.item_name, oi.model_name
                ORDER BY cnt DESC, oi.item_name ASC, oi.model_name ASC NULLS LAST
                LIMIT 3
                """,
                *item_params,
            )

        return {
            "orders_count": int(row["orders_count"] or 0),
            "revenue": int(row["revenue"] or 0),
            "asked_price_count": int(row["asked_price_count"] or 0),
            "items_count": int(items_count or 0),
            "top_items": [
                {
                    "name": f"{r['item_name']} ({r['model_name']})" if r["model_name"] else r["item_name"],
                    "count": int(r["cnt"]),
                }
                for r in top
            ],
        }

    async def get_date_summary(self, date_value: str) -> dict[str, Any]:
        async with self._pool().acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*)::bigint AS orders_count,
                    COALESCE(SUM(total_amount), 0)::bigint AS revenue,
                    COALESCE(SUM(CASE WHEN status='asked_price' THEN 1 ELSE 0 END), 0)::bigint AS asked_price_count
                FROM orders
                WHERE (created_at AT TIME ZONE 'Asia/Tashkent')::date = $1::date
                """,
                date_value,
            )

            items_count = await conn.fetchval(
                """
                SELECT COUNT(*)::bigint
                FROM order_items oi
                JOIN orders o ON o.id=oi.order_id
                WHERE (o.created_at AT TIME ZONE 'Asia/Tashkent')::date = $1::date
                """,
                date_value,
            )

            top = await conn.fetch(
                """
                SELECT
                    oi.item_name,
                    oi.model_name,
                    COUNT(*)::bigint AS cnt
                FROM order_items oi
                JOIN orders o ON o.id=oi.order_id
                WHERE (o.created_at AT TIME ZONE 'Asia/Tashkent')::date = $1::date
                GROUP BY oi.item_name, oi.model_name
                ORDER BY cnt DESC, oi.item_name ASC, oi.model_name ASC NULLS LAST
                LIMIT 3
                """,
                date_value,
            )

        return {
            "orders_count": int(row["orders_count"] or 0),
            "revenue": int(row["revenue"] or 0),
            "asked_price_count": int(row["asked_price_count"] or 0),
            "items_count": int(items_count or 0),
            "top_items": [
                {
                    "name": f"{r['item_name']} ({r['model_name']})" if r["model_name"] else r["item_name"],
                    "count": int(r["cnt"]),
                }
                for r in top
            ],
        }

    async def get_today_summary(self) -> dict[str, int]:
        data = await self.get_period_summary(days=1)
        return {
            "orders_count": data["orders_count"],
            "revenue": data["revenue"],
            "items_count": data["items_count"],
            "asked_price_count": data["asked_price_count"],
        }

    async def get_top_items_today(self, limit: int = 3) -> list[dict[str, Any]]:
        async with self._pool().acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT oi.item_name, oi.model_name, COUNT(*)::bigint AS cnt
                FROM order_items oi
                JOIN orders o ON o.id=oi.order_id
                WHERE (o.created_at AT TIME ZONE 'Asia/Tashkent')::date = (now() AT TIME ZONE 'Asia/Tashkent')::date
                GROUP BY oi.item_name, oi.model_name
                ORDER BY cnt DESC, oi.item_name ASC, oi.model_name ASC NULLS LAST
                LIMIT $1
                """,
                limit,
            )
        return [
            {
                "item_name": f"{r['item_name']} ({r['model_name']})" if r["model_name"] else r["item_name"],
                "count": int(r["cnt"]),
            }
            for r in rows
        ]

    async def safe_call(self, coro, default):
        try:
            return await coro
        except Exception as exc:  # pragma: no cover
            logging.exception("DB xatolik: %s", exc)
            return default
