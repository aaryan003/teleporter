-- ============================================
-- Migration 002: Rider Applications Table
-- Teleporter Rider Onboarding Flow
-- ============================================

-- Application status ENUM
DO $$ BEGIN
    CREATE TYPE application_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Rider Applications table — stores onboarding applications
-- Riders are NOT inserted into the `riders` table until approved.
CREATE TABLE IF NOT EXISTS rider_applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    vehicle vehicle_type NOT NULL DEFAULT 'BIKE',
    vehicle_reg VARCHAR(30),
    license_file_id VARCHAR(255),       -- Telegram file_id for license photo
    license_file_url TEXT,              -- Stored URL/path after download
    aadhar_file_id VARCHAR(255),        -- Optional: ID proof Telegram file_id
    aadhar_file_url TEXT,               -- Stored URL/path after download
    preferred_warehouse_id UUID REFERENCES warehouses(id) ON DELETE SET NULL,
    status application_status DEFAULT 'PENDING',
    admin_note TEXT,
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_rider_applications_telegram ON rider_applications(telegram_id);
CREATE INDEX IF NOT EXISTS idx_rider_applications_status ON rider_applications(status);
CREATE INDEX IF NOT EXISTS idx_rider_applications_created ON rider_applications(created_at DESC);

-- Trigger for updated_at
CREATE TRIGGER trg_rider_applications_updated
    BEFORE UPDATE ON rider_applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
