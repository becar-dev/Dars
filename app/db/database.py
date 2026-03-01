"""SQLite database layer for order-based CRM operations."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

STATUS_LABELS = {
    "asked_price": "Faqat narx so‘radi",
    "ordered": "Buyurtma berdi",
    "urgent": "Shoshildi",
    "returned": "Qaytib keldi",
}


class Database:
    """Simple sqlite wrapper.

    This project runs in single-process local polling mode, and each operation
    uses a short-lived sqlite connection, which is safe for this usage pattern.
    """

    def __init__(self, db_path: str = "crm.db") -> None:
        self.db_path = db_path
        Path(self.db_path).touch(exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL CHECK(status IN ('asked_price', 'ordered', 'urgent', 'returned')),
                    customer_type TEXT NOT NULL CHECK(customer_type IN ('walk_in', 'returning')),
                    total_amount INTEGER NOT NULL DEFAULT 0 CHECK(total_amount >= 0)
                );

                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    category TEXT NOT NULL CHECK(category IN ('service', 'stationery')),
                    item_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK(quantity > 0),
                    unit_price INTEGER NOT NULL CHECK(unit_price >= 0),
                    line_total INTEGER NOT NULL CHECK(line_total >= 0),
                    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS catalog_services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))
                );

                CREATE TABLE IF NOT EXISTS catalog_products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))
                );
                """
            )
            self._seed_catalog(conn)
            self._migrate_from_legacy_if_exists(conn)
            conn.commit()

    def _seed_catalog(self, conn: sqlite3.Connection) -> None:
        services = [
            "Vizitka",
            "Banner",
            "Laminatsiya",
            "Nusxa/Chop",
            "Skaner",
            "Dizayn",
        ]
        products = ["Ruchka", "Daftar", "Qog‘oz", "Fayl papka"]

        for service in services:
            conn.execute(
                "INSERT OR IGNORE INTO catalog_services (name, is_active) VALUES (?, 1)",
                (service,),
            )

        for product in products:
            conn.execute(
                "INSERT OR IGNORE INTO catalog_products (name, is_active) VALUES (?, 1)",
                (product,),
            )

    def _migrate_from_legacy_if_exists(self, conn: sqlite3.Connection) -> None:
        table_exists = conn.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = 'customers_log'
            """
        ).fetchone()
        if not table_exists:
            return

        marker_exists = conn.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = 'migration_meta'
            """
        ).fetchone()
        if not marker_exists:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS migration_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

        already = conn.execute(
            "SELECT value FROM migration_meta WHERE key = 'legacy_customers_log_migrated'"
        ).fetchone()
        if already and already["value"] == "1":
            return

        legacy_rows = conn.execute(
            "SELECT date, service, status, amount FROM customers_log ORDER BY id ASC"
        ).fetchall()

        status_map = {
            "Asked price only": "asked_price",
            "Placed order": "ordered",
            "Urgent client": "urgent",
            "Returning customer": "returned",
        }

        for row in legacy_rows:
            status = status_map.get(row["status"], "ordered")
            customer_type = "returning" if status == "returned" else "walk_in"
            order_cur = conn.execute(
                """
                INSERT INTO orders (created_at, status, customer_type, total_amount)
                VALUES (?, ?, ?, ?)
                """,
                (row["date"], status, customer_type, max(0, int(row["amount"]))),
            )
            order_id = order_cur.lastrowid
            line_total = max(0, int(row["amount"]))
            conn.execute(
                """
                INSERT INTO order_items (order_id, category, item_name, quantity, unit_price, line_total)
                VALUES (?, 'service', ?, 1, ?, ?)
                """,
                (order_id, row["service"], line_total, line_total),
            )
            conn.execute(
                "INSERT OR IGNORE INTO catalog_services (name, is_active) VALUES (?, 1)",
                (row["service"],),
            )

        conn.execute(
            """
            INSERT INTO migration_meta (key, value)
            VALUES ('legacy_customers_log_migrated', '1')
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """
        )

    def get_catalog_items(self, category: str) -> list[str]:
        table = "catalog_services" if category == "service" else "catalog_products"
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT name FROM {table} WHERE is_active = 1 ORDER BY name ASC"
            ).fetchall()
        return [row["name"] for row in rows]

    def add_catalog_item(self, category: str, name: str) -> bool:
        table = "catalog_services" if category == "service" else "catalog_products"
        cleaned = name.strip()
        if not cleaned:
            return False
        with self._connect() as conn:
            conn.execute(
                f"INSERT OR IGNORE INTO {table} (name, is_active) VALUES (?, 1)",
                (cleaned,),
            )
            conn.commit()
            exists = conn.execute(
                f"SELECT 1 FROM {table} WHERE name = ?",
                (cleaned,),
            ).fetchone()
        return bool(exists)

    def create_order(self, status: str, customer_type: str, items: list[dict[str, Any]]) -> int:
        """Create order and all items in a single transaction."""

        total_amount = sum(int(item["line_total"]) for item in items)

        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO orders (status, customer_type, total_amount)
                VALUES (?, ?, ?)
                """,
                (status, customer_type, total_amount),
            )
            order_id = cur.lastrowid

            for item in items:
                conn.execute(
                    """
                    INSERT INTO order_items
                    (order_id, category, item_name, quantity, unit_price, line_total)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_id,
                        item["category"],
                        item["item_name"],
                        int(item["quantity"]),
                        int(item["unit_price"]),
                        int(item["line_total"]),
                    ),
                )
            conn.commit()
        return order_id

    def fetch_today_statistics(self) -> dict[str, Any]:
        with self._connect() as conn:
            orders_count = conn.execute(
                """
                SELECT COUNT(*) AS value
                FROM orders
                WHERE date(created_at, 'localtime') = date('now', 'localtime')
                """
            ).fetchone()["value"]

            items_count = conn.execute(
                """
                SELECT COUNT(*) AS value
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE date(o.created_at, 'localtime') = date('now', 'localtime')
                """
            ).fetchone()["value"]

            revenue = conn.execute(
                """
                SELECT COALESCE(SUM(total_amount), 0) AS value
                FROM orders
                WHERE date(created_at, 'localtime') = date('now', 'localtime')
                """
            ).fetchone()["value"]

            asked_price_count = conn.execute(
                """
                SELECT COUNT(*) AS value
                FROM orders
                WHERE date(created_at, 'localtime') = date('now', 'localtime')
                  AND status = 'asked_price'
                """
            ).fetchone()["value"]

            top_item = conn.execute(
                """
                SELECT oi.item_name, COUNT(*) AS cnt
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE date(o.created_at, 'localtime') = date('now', 'localtime')
                GROUP BY oi.item_name
                ORDER BY cnt DESC, oi.item_name ASC
                LIMIT 1
                """
            ).fetchone()

        return {
            "orders_count": orders_count,
            "items_count": items_count,
            "revenue": revenue,
            "asked_price_count": asked_price_count,
            "top_item": top_item["item_name"] if top_item else "Ma'lumot yo‘q",
        }

    def fetch_weekly_statistics(self) -> dict[str, Any]:
        with self._connect() as conn:
            orders_count = conn.execute(
                """
                SELECT COUNT(*) AS value
                FROM orders
                WHERE date(created_at, 'localtime') >= date('now', '-6 days', 'localtime')
                """
            ).fetchone()["value"]

            revenue = conn.execute(
                """
                SELECT COALESCE(SUM(total_amount), 0) AS value
                FROM orders
                WHERE date(created_at, 'localtime') >= date('now', '-6 days', 'localtime')
                """
            ).fetchone()["value"]

            top3 = conn.execute(
                """
                SELECT oi.item_name, COUNT(*) AS cnt
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE date(o.created_at, 'localtime') >= date('now', '-6 days', 'localtime')
                GROUP BY oi.item_name
                ORDER BY cnt DESC, oi.item_name ASC
                LIMIT 3
                """
            ).fetchall()

        return {
            "orders_count": orders_count,
            "revenue": revenue,
            "top3": [row["item_name"] for row in top3],
        }

    def fetch_service_report(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    oi.category,
                    oi.item_name,
                    COUNT(*) AS count,
                    COALESCE(SUM(oi.line_total), 0) AS revenue,
                    CAST(AVG(oi.line_total) AS INTEGER) AS avg_check
                FROM order_items oi
                GROUP BY oi.category, oi.item_name
                ORDER BY oi.category ASC, count DESC, oi.item_name ASC
                """
            ).fetchall()

        return [
            {
                "category": row["category"],
                "item_name": row["item_name"],
                "count": row["count"],
                "revenue": row["revenue"],
                "avg_check": row["avg_check"] or 0,
            }
            for row in rows
        ]

    def status_label(self, status: str) -> str:
        return STATUS_LABELS.get(status, status)
