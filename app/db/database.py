"""SQLite database access layer for CRM operations."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class Database:
    """Simple wrapper around sqlite3 connection for CRM data operations."""

    def __init__(self, db_path: str = "crm.db") -> None:
        self.db_path = db_path
        Path(self.db_path).touch(exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        """Create required table if it does not exist."""

        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS customers_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    service TEXT NOT NULL,
                    status TEXT NOT NULL,
                    amount INTEGER NOT NULL
                )
                """
            )
            conn.commit()

    def add_customer_log(self, service: str, status: str, amount: int) -> None:
        """Insert one customer interaction into the log."""

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO customers_log (service, status, amount)
                VALUES (?, ?, ?)
                """,
                (service, status, amount),
            )
            conn.commit()

    def fetch_today_statistics(self) -> dict[str, int]:
        """Return today's KPI values."""

        with self._connect() as conn:
            total_visitors = conn.execute(
                """
                SELECT COUNT(*) AS value
                FROM customers_log
                WHERE date(date, 'localtime') = date('now', 'localtime')
                """
            ).fetchone()["value"]

            real_orders = conn.execute(
                """
                SELECT COUNT(*) AS value
                FROM customers_log
                WHERE date(date, 'localtime') = date('now', 'localtime')
                  AND status = 'Placed order'
                """
            ).fetchone()["value"]

            price_inquiries = conn.execute(
                """
                SELECT COUNT(*) AS value
                FROM customers_log
                WHERE date(date, 'localtime') = date('now', 'localtime')
                  AND status = 'Asked price only'
                """
            ).fetchone()["value"]

            revenue = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0) AS value
                FROM customers_log
                WHERE date(date, 'localtime') = date('now', 'localtime')
                """
            ).fetchone()["value"]

        return {
            "total_visitors": total_visitors,
            "real_orders": real_orders,
            "price_inquiries": price_inquiries,
            "revenue": revenue,
        }

    def fetch_weekly_statistics(self) -> dict[str, Any]:
        """Return summarized stats for the last 7 days including today."""

        with self._connect() as conn:
            base_query_filter = "date(date, 'localtime') >= date('now', '-6 days', 'localtime')"

            total_visitors = conn.execute(
                f"SELECT COUNT(*) AS value FROM customers_log WHERE {base_query_filter}"
            ).fetchone()["value"]

            revenue = conn.execute(
                f"SELECT COALESCE(SUM(amount), 0) AS value FROM customers_log WHERE {base_query_filter}"
            ).fetchone()["value"]

            top_service_row = conn.execute(
                f"""
                SELECT service, COUNT(*) AS cnt
                FROM customers_log
                WHERE {base_query_filter}
                GROUP BY service
                ORDER BY cnt DESC, service ASC
                LIMIT 1
                """
            ).fetchone()

        return {
            "total_visitors": total_visitors,
            "revenue": revenue,
            "most_requested_service": top_service_row["service"] if top_service_row else "No data yet",
        }

    def fetch_service_report(self) -> list[dict[str, Any]]:
        """Return per-service aggregated report for all time."""

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    service,
                    COUNT(*) AS requested_count,
                    SUM(CASE WHEN status = 'Placed order' THEN 1 ELSE 0 END) AS actual_orders,
                    COALESCE(SUM(amount), 0) AS revenue
                FROM customers_log
                GROUP BY service
                ORDER BY requested_count DESC, service ASC
                """
            ).fetchall()

        return [
            {
                "service": row["service"],
                "requested_count": row["requested_count"],
                "actual_orders": row["actual_orders"],
                "revenue": row["revenue"],
            }
            for row in rows
        ]
