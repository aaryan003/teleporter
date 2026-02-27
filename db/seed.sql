-- ============================================
-- TeleporterBot v2 — Seed Data for Demo
-- ============================================

-- Default warehouse
INSERT INTO warehouses (id, name, address, lat, lng, city, capacity)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'TeleporterBot Central Hub',
    'Koramangala 4th Block, Bangalore',
    12.9352,
    77.6245,
    'Bangalore',
    500
);

-- Demo rider accounts (company employees)
INSERT INTO riders (id, telegram_id, employee_id, full_name, phone, vehicle, vehicle_reg, warehouse_id, status, shift_start, shift_end)
VALUES
    ('b0000000-0000-0000-0000-000000000001', 100000001, 'EMP-001', 'Rajesh Kumar', '+919876543001', 'BIKE', 'KA01AB1234', 'a0000000-0000-0000-0000-000000000001', 'ON_DUTY', '08:00', '20:00'),
    ('b0000000-0000-0000-0000-000000000002', 100000002, 'EMP-002', 'Suresh Patel', '+919876543002', 'AUTO', 'KA01CD5678', 'a0000000-0000-0000-0000-000000000001', 'ON_DUTY', '08:00', '20:00'),
    ('b0000000-0000-0000-0000-000000000003', 100000003, 'EMP-003', 'Amit Singh', '+919876543003', 'VAN', 'KA01EF9012', 'a0000000-0000-0000-0000-000000000001', 'ON_DUTY', '09:00', '21:00'),
    ('b0000000-0000-0000-0000-000000000004', 100000004, 'EMP-004', 'Priya Sharma', '+919876543004', 'BIKE', 'KA01GH3456', 'a0000000-0000-0000-0000-000000000001', 'OFF_DUTY', '10:00', '22:00'),
    ('b0000000-0000-0000-0000-000000000005', 100000005, 'EMP-005', 'Vikram Reddy', '+919876543005', 'AUTO', 'KA01IJ7890', 'a0000000-0000-0000-0000-000000000001', 'ON_DUTY', '06:00', '18:00');

-- Default surge zone
INSERT INTO surge_zones (name, city, center_lat, center_lng, radius_km)
VALUES
    ('Koramangala', 'Bangalore', 12.9352, 77.6245, 5.0),
    ('Indiranagar', 'Bangalore', 12.9784, 77.6408, 4.0),
    ('HSR Layout', 'Bangalore', 12.9116, 77.6389, 4.0),
    ('Whitefield', 'Bangalore', 12.9698, 77.7500, 6.0);
