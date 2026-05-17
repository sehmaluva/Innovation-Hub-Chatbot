-- ============================================================
-- Innovation Hub Challenge — Database Schema
-- MSSQL (SQL Server 2019+)
-- ============================================================

USE master;
GO

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'Chatbot')
BEGIN
    CREATE DATABASE Chatbot;
END
GO

USE Chatbot;
GO

-- ============================================================
-- Users — registered WhatsApp users
-- ============================================================
IF OBJECT_ID('dbo.Users', 'U') IS NOT NULL DROP TABLE dbo.Users;
GO

CREATE TABLE dbo.Users (
    user_id       INT IDENTITY(1,1) PRIMARY KEY,
    phone_number  NVARCHAR(20)  NOT NULL UNIQUE,   -- E.164 format e.g. +260977123456
    full_name     NVARCHAR(100) NOT NULL,
    email         NVARCHAR(150) NULL,
    is_active     BIT           NOT NULL DEFAULT 1,
    created_at    DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
    updated_at    DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

-- ============================================================
-- Instruments — tradable assets (stocks, ETFs, etc.)
-- ============================================================
IF OBJECT_ID('dbo.Instruments', 'U') IS NOT NULL DROP TABLE dbo.Instruments;
GO

CREATE TABLE dbo.Instruments (
    instrument_id  INT IDENTITY(1,1) PRIMARY KEY,
    symbol         NVARCHAR(20)   NOT NULL UNIQUE,  -- e.g. ZANACO, MTN, ZCCM
    name           NVARCHAR(100)  NOT NULL,
    sector         NVARCHAR(80)   NULL,
    currency       NCHAR(3)       NOT NULL DEFAULT 'ZMW',
    is_active      BIT            NOT NULL DEFAULT 1,
    created_at     DATETIME2      NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

-- ============================================================
-- Prices — latest price per instrument (one row per symbol)
-- ============================================================
IF OBJECT_ID('dbo.Prices', 'U') IS NOT NULL DROP TABLE dbo.Prices;
GO

CREATE TABLE dbo.Prices (
    price_id       INT IDENTITY(1,1) PRIMARY KEY,
    instrument_id  INT            NOT NULL REFERENCES dbo.Instruments(instrument_id),
    bid_price      DECIMAL(18,4)  NOT NULL,
    ask_price      DECIMAL(18,4)  NOT NULL,
    last_price     DECIMAL(18,4)  NOT NULL,
    change_pct     DECIMAL(8,4)   NOT NULL DEFAULT 0,   -- % change from previous close
    volume         BIGINT         NOT NULL DEFAULT 0,
    recorded_at    DATETIME2      NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

-- Index for fast lookups by instrument + time
CREATE NONCLUSTERED INDEX IX_Prices_Instrument_Time
    ON dbo.Prices (instrument_id, recorded_at DESC);
GO

-- ============================================================
-- Orders — buy / sell orders placed by users
-- ============================================================
IF OBJECT_ID('dbo.Orders', 'U') IS NOT NULL DROP TABLE dbo.Orders;
GO

CREATE TABLE dbo.Orders (
    order_id       INT IDENTITY(1,1) PRIMARY KEY,
    user_id        INT            NOT NULL REFERENCES dbo.Users(user_id),
    instrument_id  INT            NOT NULL REFERENCES dbo.Instruments(instrument_id),
    order_type     NVARCHAR(4)    NOT NULL CHECK (order_type IN ('BUY', 'SELL')),
    quantity       INT            NOT NULL CHECK (quantity > 0),
    limit_price    DECIMAL(18,4)  NULL,      -- NULL = market order
    executed_price DECIMAL(18,4)  NULL,      -- filled at this price
    status         NVARCHAR(12)   NOT NULL DEFAULT 'PENDING'
                                  CHECK (status IN ('PENDING', 'EXECUTED', 'CANCELLED', 'REJECTED')),
    notes          NVARCHAR(500)  NULL,
    placed_at      DATETIME2      NOT NULL DEFAULT SYSUTCDATETIME(),
    executed_at    DATETIME2      NULL,
    cancelled_at   DATETIME2      NULL
);
GO

CREATE NONCLUSTERED INDEX IX_Orders_User
    ON dbo.Orders (user_id, placed_at DESC);
GO

CREATE NONCLUSTERED INDEX IX_Orders_Status
    ON dbo.Orders (status, placed_at DESC);
GO

-- ============================================================
-- Portfolio — aggregated holdings per user per instrument
-- ============================================================
IF OBJECT_ID('dbo.Portfolio', 'U') IS NOT NULL DROP TABLE dbo.Portfolio;
GO

CREATE TABLE dbo.Portfolio (
    portfolio_id   INT IDENTITY(1,1) PRIMARY KEY,
    user_id        INT            NOT NULL REFERENCES dbo.Users(user_id),
    instrument_id  INT            NOT NULL REFERENCES dbo.Instruments(instrument_id),
    quantity       INT            NOT NULL DEFAULT 0,
    avg_cost       DECIMAL(18,4)  NOT NULL DEFAULT 0,   -- average cost basis
    total_invested DECIMAL(18,4)  NOT NULL DEFAULT 0,
    updated_at     DATETIME2      NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_Portfolio_User_Instrument UNIQUE (user_id, instrument_id)
);
GO

PRINT 'Schema created successfully.';
GO
