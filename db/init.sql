-- Core TeleporterBot v2 schema (no admin UI or n8n required)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- USERS (minimal)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE,
    full_name VARCHAR(255),
    phone VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- WAREHOUSES
CREATE TABLE IF NOT EXISTS warehouses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

-- RIDERS (company employees)
CREATE TABLE IF NOT EXISTS riders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    employee_id VARCHAR(20) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    vehicle_type VARCHAR(20) NOT NULL,
    vehicle_reg VARCHAR(20),
    warehouse_id UUID REFERENCES warehouses(id),
    current_lat DECIMAL(10, 7),
    current_lng DECIMAL(10, 7),
    status VARCHAR(20) DEFAULT 'OFF_DUTY',
    shift_start TIME,
    shift_end TIME,
    max_capacity INT DEFAULT 5,
    current_load INT DEFAULT 0,
    rating DECIMAL(3, 2) DEFAULT 5.00,
    total_deliveries INT DEFAULT 0,
    last_location_update TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ORDER STATUS ENUM
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_status') THEN
        CREATE TYPE order_status AS ENUM (
            'ORDER_PLACED', 'PAYMENT_CONFIRMED', 'PICKUP_SCHEDULED',
            'PICKUP_RIDER_ASSIGNED', 'PICKUP_EN_ROUTE', 'PICKED_UP',
            'IN_TRANSIT_TO_WAREHOUSE', 'AT_WAREHOUSE',
            'ROUTE_OPTIMIZED', 'DELIVERY_RIDER_ASSIGNED', 'OUT_FOR_DELIVERY',
            'DELIVERED', 'COMPLETED', 'CANCELLED', 'REFUNDED'
        );
    END IF;
END
$$;

-- DELIVERY ROUTES
CREATE TABLE IF NOT EXISTS delivery_routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rider_id UUID REFERENCES riders(id),
    warehouse_id UUID REFERENCES warehouses(id),
    status VARCHAR(20) DEFAULT 'PLANNED',
    optimized_sequence JSONB NOT NULL,
    total_distance_km DECIMAL(8, 2),
    total_duration_min INT,
    total_parcels INT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ORDERS
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number VARCHAR(20) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id),

    pickup_rider_id UUID REFERENCES riders(id),
    pickup_slot TIMESTAMPTZ,
    pickup_address TEXT NOT NULL,
    pickup_lat DECIMAL(10, 7),
    pickup_lng DECIMAL(10, 7),
    pickup_otp VARCHAR(6),
    pickup_confirmed_at TIMESTAMPTZ,

    warehouse_id UUID REFERENCES warehouses(id),
    warehouse_received_at TIMESTAMPTZ,

    delivery_rider_id UUID REFERENCES riders(id),
    delivery_route_id UUID REFERENCES delivery_routes(id),
    drop_address TEXT NOT NULL,
    drop_lat DECIMAL(10, 7),
    drop_lng DECIMAL(10, 7),
    drop_otp VARCHAR(6),

    weight_kg DECIMAL(5, 2),
    weight_tier VARCHAR(10),
    vehicle_type VARCHAR(20),

    distance_km DECIMAL(8, 2),
    base_cost DECIMAL(10, 2),
    surge_multiplier DECIMAL(3, 2) DEFAULT 1.00,
    addons_cost DECIMAL(10, 2) DEFAULT 0,
    total_cost DECIMAL(10, 2),

    status order_status DEFAULT 'ORDER_PLACED',
    is_express BOOLEAN DEFAULT FALSE,
    is_batch_eligible BOOLEAN DEFAULT TRUE,
    is_return_trip_pickup BOOLEAN DEFAULT FALSE,

    payment_status VARCHAR(20) DEFAULT 'PENDING',
    razorpay_order_id VARCHAR(255),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ
);

-- SUBSCRIPTIONS
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    plan VARCHAR(20) NOT NULL,
    monthly_price DECIMAL(10, 2) NOT NULL,
    free_deliveries_remaining INT DEFAULT 0,
    starts_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    razorpay_subscription_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI INSIGHTS (for future admin analytics)
CREATE TABLE IF NOT EXISTS ai_insights (
    id BIGSERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    insight TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'INFO',
    data JSONB,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- GEO CACHE
CREATE TABLE IF NOT EXISTS geo_cache (
    address_hash VARCHAR(64) PRIMARY KEY,
    address TEXT NOT NULL,
    lat DECIMAL(10, 7),
    lng DECIMAL(10, 7),
    cached_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '30 days'
);

