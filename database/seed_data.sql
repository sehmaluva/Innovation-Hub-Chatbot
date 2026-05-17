-- ============================================================
-- Innovation Hub Challenge — Seed / Sample Data
-- Run AFTER schema.sql
-- ============================================================

USE Chatbot;
GO

-- ---- Instruments ----
INSERT INTO dbo.Instruments (symbol, name, sector, currency) VALUES
('ZANACO',  'Zambia National Commercial Bank',  'Financial Services', 'ZMW'),
('ZCCM',    'ZCCM Investments Holdings',         'Mining',             'ZMW'),
('ZSUG',    'Zambia Sugar',                      'Agriculture',        'ZMW'),
('PUMA',    'Puma Energy Zambia',                'Energy',             'ZMW'),
('NANGA',   'Nanga Farms',                       'Agriculture',        'ZMW'),
('BATA',    'Bata Shoes',                        'Consumer Goods',     'ZMW'),
('PRIMA',   'Prima Reinsurance',                 'Insurance',          'ZMW'),
('LAFARGE', 'Lafarge Zambia',                    'Industrial',         'ZMW');
GO

-- ---- Latest Prices ----
INSERT INTO dbo.Prices (instrument_id, bid_price, ask_price, last_price, change_pct, volume) VALUES
(1, 2.80, 2.85, 2.82,  1.44,  45200),
(2, 9.10, 9.20, 9.15, -0.54,  12300),
(3, 5.40, 5.50, 5.45,  0.93,  30100),
(4, 4.20, 4.30, 4.25, -1.16,   8700),
(5, 1.30, 1.35, 1.32,  2.33,  21000),
(6, 3.55, 3.65, 3.60,  0.00,   5400),
(7, 0.85, 0.90, 0.87, -1.14,  67000),
(8, 6.70, 6.80, 6.75,  0.75,  14800);
GO

-- ---- Demo Users ----
INSERT INTO dbo.Users (phone_number, full_name, email) VALUES
('+260971000001', 'Alice Banda',   'alice@example.com'),
('+260971000002', 'Bob Mwale',     'bob@example.com'),
('+260971000003', 'Carol Tembo',   'carol@example.com');
GO

-- ---- Demo Portfolio (Alice holds ZANACO and ZCCM) ----
INSERT INTO dbo.Portfolio (user_id, instrument_id, quantity, avg_cost, total_invested) VALUES
(1, 1, 500, 2.60, 1300.00),
(1, 2, 100, 8.90,  890.00);
GO

-- ---- Demo Orders ----
INSERT INTO dbo.Orders (user_id, instrument_id, order_type, quantity, limit_price, executed_price, status, executed_at) VALUES
(1, 1, 'BUY',  500, 2.62, 2.60, 'EXECUTED', DATEADD(day, -10, SYSUTCDATETIME())),
(1, 2, 'BUY',  100, 9.00, 8.90, 'EXECUTED', DATEADD(day, -5,  SYSUTCDATETIME())),
(2, 3, 'BUY',  200, NULL, NULL,  'PENDING',  NULL),
(3, 1, 'SELL', 100, 2.90, NULL,  'PENDING',  NULL);
GO

PRINT 'Seed data inserted successfully.';
GO
