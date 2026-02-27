-- ============================================
-- TeleporterBot v2 — Seed Data for Demo
-- ============================================

-- Default warehouse
INSERT INTO warehouses (id, name, address, lat, lng, city, capacity)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'TeleporterBot Central Hub',
    '1200 Market Street, San Francisco, CA 94103',
    37.7790,
    -122.4138,
    'San Francisco',
    500
);

-- Demo driver accounts (company employees)
INSERT INTO riders (id, telegram_id, employee_id, full_name, phone, vehicle, vehicle_reg, warehouse_id, status, shift_start, shift_end)
VALUES
    ('b0000000-0000-0000-0000-000000000001', 100000001, 'EMP-001', 'Jake Morrison', '+14155551001', 'BIKE', 'CA-BK-1234', 'a0000000-0000-0000-0000-000000000001', 'ON_DUTY', '08:00', '20:00'),
    ('b0000000-0000-0000-0000-000000000002', 100000002, 'EMP-002', 'Sarah Chen', '+14155551002', 'MINI_VAN', 'CA-7ABC123', 'a0000000-0000-0000-0000-000000000001', 'ON_DUTY', '08:00', '20:00'),
    ('b0000000-0000-0000-0000-000000000003', 100000003, 'EMP-003', 'Marcus Williams', '+14155551003', 'TRUCK', 'CA-8XYZ789', 'a0000000-0000-0000-0000-000000000001', 'ON_DUTY', '09:00', '21:00'),
    ('b0000000-0000-0000-0000-000000000004', 100000004, 'EMP-004', 'Emily Rodriguez', '+14155551004', 'BIKE', 'CA-BK-5678', 'a0000000-0000-0000-0000-000000000001', 'OFF_DUTY', '10:00', '22:00'),
    ('b0000000-0000-0000-0000-000000000005', 100000005, 'EMP-005', 'Ryan Patel', '+14155551005', 'MINI_VAN', 'CA-7DEF456', 'a0000000-0000-0000-0000-000000000001', 'ON_DUTY', '06:00', '18:00'),
    ('b0000000-0000-0000-0000-000000000006', 100000006, 'EMP-006', 'David Kim', '+14155551006', 'MINI_TRUCK', 'CA-8GHI012', 'a0000000-0000-0000-0000-000000000001', 'ON_DUTY', '08:00', '20:00');

-- Default surge zones
INSERT INTO surge_zones (name, city, center_lat, center_lng, radius_km)
VALUES
    ('Downtown SF', 'San Francisco', 37.7749, -122.4194, 5.0),
    ('SoMa', 'San Francisco', 37.7785, -122.3950, 4.0),
    ('Mission District', 'San Francisco', 37.7599, -122.4148, 4.0),
    ('Financial District', 'San Francisco', 37.7946, -122.3999, 3.0);
