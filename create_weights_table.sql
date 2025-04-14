CREATE TABLE IF NOT EXISTS weights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sessions_weight DECIMAL(10,2) DEFAULT 1.0,
    views_weight DECIMAL(10,2) DEFAULT 1.0,
    cart_weight DECIMAL(10,2) DEFAULT 1.0,
    checkout_weight DECIMAL(10,2) DEFAULT 1.0,
    orders_gross_weight DECIMAL(10,2) DEFAULT 1.0,
    orders_net_weight DECIMAL(10,2) DEFAULT 1.0,
    discount_penalty DECIMAL(10,2) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Вставляем начальные значения
INSERT INTO weights (
    sessions_weight,
    views_weight,
    cart_weight,
    checkout_weight,
    orders_gross_weight,
    orders_net_weight,
    discount_penalty
) VALUES (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0); 