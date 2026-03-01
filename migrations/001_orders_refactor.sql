-- Migration: legacy customers_log -> orders + order_items + catalogs
-- This script is idempotent for schema creation.
-- Data migration from customers_log is intentionally executed by app code
-- (Database._migrate_from_legacy_if_exists) so it can safely check table existence.

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

-- Data migration steps (performed by application code):
-- 1) Read rows from legacy customers_log.
-- 2) Map status text:
--      Asked price only   -> asked_price
--      Placed order       -> ordered
--      Urgent client      -> urgent
--      Returning customer -> returned
-- 3) Insert one row into orders per legacy row.
-- 4) Insert one service row into order_items per order (quantity=1, unit_price=line_total=amount>=0).
-- 5) Set migration_meta('legacy_customers_log_migrated') = '1'.
-- 6) Keep customers_log table unchanged for audit/backward compatibility.
