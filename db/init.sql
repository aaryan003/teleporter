-- ============================================
-- TeleporterBot v2 — Database Schema
-- Hub-and-Spoke Logistics System
-- ============================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── ENUM TYPES ────────────────────────────────────────────

CREATE TYPE vehicle_type AS ENUM ('BIKE', 'MINI_VAN', 'MINI_TRUCK', 'TRUCK');
CREATE TYPE package_size AS ENUM ('SMALL', 'MEDIUM', 'LARGE', 'BULKY');
CREATE TYPE payment_mode AS ENUM ('COD', 'CARD', 'UPI');

CREATE TYPE order_status AS ENUM (
    'ORDER_PLACED', 'PAYMENT_CONFIRMED', 'PICKUP_SCHEDULED',
    'PICKUP_RIDER_ASSIGNED', 'PICKUP_EN_ROUTE', 'PICKED_UP',
    'IN_TRANSIT_TO_WAREHOUSE', 'AT_WAREHOUSE',
    'ROUTE_OPTIMIZED', 'DELIVERY_RIDER_ASSIGNED', 'OUT_FOR_DELIVERY',
    'DELIVERED', 'COMPLETED', 'CANCELLED', 'REFUNDED'
);

CREATE TYPE rider_status AS ENUM ('ON_DUTY', 'OFF_DUTY', 'ON_DELIVERY', 'ON_PICKUP');
CREATE TYPE payment_status AS ENUM ('PENDING', 'PAID', 'REFUNDED', 'FAILED');
CREATE TYPE subscription_plan AS ENUM ('STARTER', 'BUSINESS', 'ENTERPRISE');
CREATE TYPE insight_severity AS ENUM ('INFO', 'WARNING', 'ACTION_REQUIRED');
CREATE TYPE route_status AS ENUM ('PLANNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED');

-- ── USERS ─────────────────────────────────────────────────

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE NOT NULL,
    telegram_username VARCHAR(255),
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    is_blocked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_telegram ON users(telegram_id);

-- ── WAREHOUSES ────────────────────────────────────────────

CREATE TABLE warehouses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    lat DECIMAL(10, 7) NOT NULL,
    lng DECIMAL(10, 7) NOT NULL,
    city VARCHAR(100),
    capacity INT DEFAULT 500,
    current_load INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    operating_hours JSONB DEFAULT '{"start": "07:00", "end": "21:00"}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── RIDERS (Company Employees) ────────────────────────────

CREATE TABLE riders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE NOT NULL,
    employee_id VARCHAR(20) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    vehicle vehicle_type NOT NULL DEFAULT 'BIKE',
    vehicle_reg VARCHAR(30),
    warehouse_id UUID REFERENCES warehouses(id) ON DELETE SET NULL,
    current_lat DECIMAL(10, 7),
    current_lng DECIMAL(10, 7),
    status rider_status DEFAULT 'OFF_DUTY',
    shift_start TIME DEFAULT '08:00',
    shift_end TIME DEFAULT '20:00',
    max_capacity INT DEFAULT 5,
    current_load INT DEFAULT 0,
    rating DECIMAL(3, 2) DEFAULT 5.00,
    total_deliveries INT DEFAULT 0,
    last_location_update TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_riders_telegram ON riders(telegram_id);
CREATE INDEX idx_riders_status ON riders(status);
CREATE INDEX idx_riders_warehouse ON riders(warehouse_id);

-- ── DELIVERY ROUTES ───────────────────────────────────────

CREATE TABLE delivery_routes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rider_id UUID REFERENCES riders(id) ON DELETE SET NULL,
    warehouse_id UUID REFERENCES warehouses(id) ON DELETE SET NULL,
    status route_status DEFAULT 'PLANNED',
    optimized_sequence JSONB NOT NULL DEFAULT '[]',
    total_distance_km DECIMAL(8, 2),
    total_duration_min INT,
    total_parcels INT DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_routes_rider ON delivery_routes(rider_id);
CREATE INDEX idx_routes_status ON delivery_routes(status);

-- ── ORDERS ────────────────────────────────────────────────

CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_number VARCHAR(20) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Pickup phase
    pickup_rider_id UUID REFERENCES riders(id) ON DELETE SET NULL,
    pickup_slot TIMESTAMPTZ,
    pickup_address TEXT NOT NULL,
    pickup_lat DECIMAL(10, 7),
    pickup_lng DECIMAL(10, 7),
    pickup_otp_hash VARCHAR(128),
    pickup_otp_attempts INT DEFAULT 0,
    pickup_confirmed_at TIMESTAMPTZ,

    -- Warehouse phase
    warehouse_id UUID REFERENCES warehouses(id) ON DELETE SET NULL,
    warehouse_received_at TIMESTAMPTZ,

    -- Delivery phase
    delivery_rider_id UUID REFERENCES riders(id) ON DELETE SET NULL,
    delivery_route_id UUID REFERENCES delivery_routes(id) ON DELETE SET NULL,
    drop_address TEXT NOT NULL,
    drop_lat DECIMAL(10, 7),
    drop_lng DECIMAL(10, 7),
    drop_otp_hash VARCHAR(128),
    drop_otp_attempts INT DEFAULT 0,

    -- Package info
    package_size package_size DEFAULT 'SMALL',
    vehicle vehicle_type DEFAULT 'BIKE',
    description TEXT,

    -- Pricing
    distance_km DECIMAL(8, 2),
    duration_min INT,
    base_cost DECIMAL(10, 2),
    surge_multiplier DECIMAL(3, 2) DEFAULT 1.00,
    addons_cost DECIMAL(10, 2) DEFAULT 0.00,
    batch_discount DECIMAL(10, 2) DEFAULT 0.00,
    subscription_discount DECIMAL(10, 2) DEFAULT 0.00,
    total_cost DECIMAL(10, 2) NOT NULL,

    -- Flags
    status order_status DEFAULT 'ORDER_PLACED',
    payment payment_status DEFAULT 'PENDING',
    is_express BOOLEAN DEFAULT FALSE,
    is_batch_eligible BOOLEAN DEFAULT TRUE,
    is_return_trip_pickup BOOLEAN DEFAULT FALSE,

    -- Payment method
    payment_mode payment_mode DEFAULT 'COD',
    razorpay_order_id VARCHAR(255),
    razorpay_payment_id VARCHAR(255),

    -- Idempotency
    idempotency_key UUID UNIQUE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ
);

CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_pickup_rider ON orders(pickup_rider_id);
CREATE INDEX idx_orders_delivery_rider ON orders(delivery_rider_id);
CREATE INDEX idx_orders_warehouse ON orders(warehouse_id);
CREATE INDEX idx_orders_route ON orders(delivery_route_id);
CREATE INDEX idx_orders_created ON orders(created_at DESC);
CREATE INDEX idx_orders_number ON orders(order_number);

-- ── ORDER EVENTS (Audit Trail) ────────────────────────────

CREATE TABLE order_events (
    id BIGSERIAL PRIMARY KEY,
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
    from_status order_status,
    to_status order_status NOT NULL,
    actor_type VARCHAR(20) NOT NULL,   -- USER, RIDER, SYSTEM, N8N
    actor_id UUID,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_order ON order_events(order_id);
CREATE INDEX idx_events_created ON order_events(created_at DESC);

-- ── SUBSCRIPTIONS ─────────────────────────────────────────

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    plan subscription_plan NOT NULL,
    monthly_price DECIMAL(10, 2) NOT NULL,
    free_deliveries_total INT DEFAULT 0,
    free_deliveries_used INT DEFAULT 0,
    starts_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    razorpay_subscription_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subs_user ON subscriptions(user_id);
CREATE INDEX idx_subs_active ON subscriptions(is_active) WHERE is_active = TRUE;

-- ── AI INSIGHTS ───────────────────────────────────────────

CREATE TABLE ai_insights (
    id BIGSERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,       -- REVENUE, FLEET, DEMAND, ROUTE, CUSTOMER
    severity insight_severity DEFAULT 'INFO',
    title VARCHAR(255) NOT NULL,
    insight TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    is_read BOOLEAN DEFAULT FALSE,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days'
);

CREATE INDEX idx_insights_category ON ai_insights(category);
CREATE INDEX idx_insights_generated ON ai_insights(generated_at DESC);

-- ── GEO CACHE ─────────────────────────────────────────────

CREATE TABLE geo_cache (
    address_hash VARCHAR(64) PRIMARY KEY,
    address_raw TEXT NOT NULL,
    lat DECIMAL(10, 7) NOT NULL,
    lng DECIMAL(10, 7) NOT NULL,
    formatted_address TEXT,
    cached_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '30 days'
);

-- ── DISTANCE CACHE ────────────────────────────────────────

CREATE TABLE distance_cache (
    origin_hash VARCHAR(64) NOT NULL,
    destination_hash VARCHAR(64) NOT NULL,
    distance_km DECIMAL(8, 2) NOT NULL,
    duration_min INT NOT NULL,
    cached_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '2 hours',
    PRIMARY KEY (origin_hash, destination_hash)
);

-- ── SURGE PRICING (per-zone cache) ────────────────────────

CREATE TABLE surge_zones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    city VARCHAR(100),
    center_lat DECIMAL(10, 7) NOT NULL,
    center_lng DECIMAL(10, 7) NOT NULL,
    radius_km DECIMAL(5, 2) DEFAULT 5.0,
    current_multiplier DECIMAL(3, 2) DEFAULT 1.00,
    active_orders INT DEFAULT 0,
    available_riders INT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── HELPER: Update updated_at trigger ─────────────────────

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_riders_updated BEFORE UPDATE ON riders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_orders_updated BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ── RECIPIENT CONTACT (safe migration) ────────────────────
-- These columns capture the drop-off recipient so the bot can
-- forward their Drop-off OTP directly to them on Telegram.

ALTER TABLE orders ADD COLUMN IF NOT EXISTS drop_contact_name    VARCHAR(255);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS drop_contact_phone   VARCHAR(20);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS drop_contact_telegram_id BIGINT;

