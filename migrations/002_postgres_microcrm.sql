-- PostgreSQL migration for cloud-ready micro-CRM

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

INSERT INTO catalog_services(name, is_active) VALUES
('Nusxa', TRUE),
('Kitob', TRUE),
('Chop', TRUE),
('Dizayn', TRUE)
ON CONFLICT (name) DO NOTHING;

INSERT INTO catalog_products(name, is_active) VALUES
('Ruchka', TRUE),
('Daftar', TRUE),
('Marker', TRUE)
ON CONFLICT (name) DO NOTHING;
