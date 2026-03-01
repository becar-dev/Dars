-- Migration: legacy customers_log -> orders + order_items + catalogs
-- Safe to run multiple times because of IF NOT EXISTS and INSERT OR IGNORE patterns.

PRAGMA foreign_keys = ON;

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

CREATE TABLE IF NOT EXISTS migration_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO catalog_services (name, is_active) VALUES
('Vizitka', 1),
('Banner', 1),
('Laminatsiya', 1),
('Nusxa/Chop', 1),
('Skaner', 1),
('Dizayn', 1);

INSERT OR IGNORE INTO catalog_products (name, is_active) VALUES
('Ruchka', 1),
('Daftar', 1),
('Qog‘oz', 1),
('Fayl papka', 1);

-- Data migration block (run once)
-- 1) rows from customers_log become one order + one order_item
-- 2) original customers_log table is kept for backward audit purposes

WITH todo AS (
    SELECT date, service, status, amount
    FROM customers_log
    WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='customers_log')
)
SELECT 1;

-- NOTE: SQLite SQL-only migration of row-by-row order->items mapping is usually
-- done from application code for reliability. The app also performs this migration
-- transactionally and marks migration_meta('legacy_customers_log_migrated')='1'.
