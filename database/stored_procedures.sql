-- ============================================================
-- Innovation Hub Challenge — Stored Procedures
-- ============================================================

USE Chatbot;
GO

-- ---- Get latest price for every active instrument ----
CREATE OR ALTER PROCEDURE dbo.sp_GetAllPrices
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        i.symbol,
        i.name,
        i.currency,
        p.bid_price,
        p.ask_price,
        p.last_price,
        p.change_pct,
        p.volume,
        p.recorded_at
    FROM dbo.Instruments i
    CROSS APPLY (
        SELECT TOP 1 *
        FROM dbo.Prices px
        WHERE px.instrument_id = i.instrument_id
        ORDER BY px.recorded_at DESC
    ) p
    WHERE i.is_active = 1
    ORDER BY i.symbol;
END;
GO

-- ---- Get latest price for a single symbol ----
CREATE OR ALTER PROCEDURE dbo.sp_GetPrice
    @symbol NVARCHAR(20)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        i.symbol,
        i.name,
        i.currency,
        p.bid_price,
        p.ask_price,
        p.last_price,
        p.change_pct,
        p.volume,
        p.recorded_at
    FROM dbo.Instruments i
    CROSS APPLY (
        SELECT TOP 1 *
        FROM dbo.Prices px
        WHERE px.instrument_id = i.instrument_id
        ORDER BY px.recorded_at DESC
    ) p
    WHERE i.symbol = UPPER(@symbol)
      AND i.is_active = 1;
END;
GO

-- ---- Place an order ----
CREATE OR ALTER PROCEDURE dbo.sp_PlaceOrder
    @phone_number  NVARCHAR(20),
    @symbol        NVARCHAR(20),
    @order_type    NVARCHAR(4),
    @quantity      INT,
    @limit_price   DECIMAL(18,4) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @user_id       INT;
    DECLARE @instrument_id INT;
    DECLARE @order_id      INT;
    DECLARE @msg           NVARCHAR(500);

    -- Resolve user
    SELECT @user_id = user_id FROM dbo.Users WHERE phone_number = @phone_number AND is_active = 1;
    IF @user_id IS NULL
    BEGIN
        SELECT -1 AS order_id, 'User not found. Please register first.' AS message;
        RETURN;
    END

    -- Resolve instrument
    SELECT @instrument_id = instrument_id FROM dbo.Instruments WHERE symbol = UPPER(@symbol) AND is_active = 1;
    IF @instrument_id IS NULL
    BEGIN
        SELECT -2 AS order_id, 'Instrument not found: ' + @symbol AS message;
        RETURN;
    END

    -- Validate SELL — user must hold enough shares
    IF @order_type = 'SELL'
    BEGIN
        DECLARE @held INT = 0;
        SELECT @held = ISNULL(quantity, 0) FROM dbo.Portfolio WHERE user_id = @user_id AND instrument_id = @instrument_id;
        IF @held < @quantity
        BEGIN
            SELECT -3 AS order_id, 'Insufficient holdings. You hold ' + CAST(@held AS NVARCHAR) + ' shares of ' + UPPER(@symbol) AS message;
            RETURN;
        END
    END

    -- Insert order
    INSERT INTO dbo.Orders (user_id, instrument_id, order_type, quantity, limit_price)
    VALUES (@user_id, @instrument_id, UPPER(@order_type), @quantity, @limit_price);

    SET @order_id = SCOPE_IDENTITY();
    SET @msg = UPPER(@order_type) + ' order placed for ' + CAST(@quantity AS NVARCHAR) + ' x ' + UPPER(@symbol) + '. Order ID: ' + CAST(@order_id AS NVARCHAR);

    SELECT @order_id AS order_id, @msg AS message;
END;
GO

-- ---- Get portfolio for a user ----
CREATE OR ALTER PROCEDURE dbo.sp_GetPortfolio
    @phone_number NVARCHAR(20)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        i.symbol,
        i.name,
        pf.quantity,
        pf.avg_cost,
        pf.total_invested,
        p.last_price,
        (p.last_price - pf.avg_cost) * pf.quantity AS unrealised_pnl,
        CASE WHEN pf.avg_cost > 0
             THEN ROUND(((p.last_price - pf.avg_cost) / pf.avg_cost) * 100, 2)
             ELSE 0 END AS return_pct
    FROM dbo.Portfolio pf
    JOIN dbo.Users u ON u.user_id = pf.user_id
    JOIN dbo.Instruments i ON i.instrument_id = pf.instrument_id
    CROSS APPLY (
        SELECT TOP 1 last_price
        FROM dbo.Prices px
        WHERE px.instrument_id = pf.instrument_id
        ORDER BY px.recorded_at DESC
    ) p
    WHERE u.phone_number = @phone_number
      AND pf.quantity > 0
    ORDER BY i.symbol;
END;
GO

-- ---- Get order history for a user ----
CREATE OR ALTER PROCEDURE dbo.sp_GetOrderHistory
    @phone_number NVARCHAR(20),
    @limit        INT = 10
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP (@limit)
        o.order_id,
        i.symbol,
        o.order_type,
        o.quantity,
        o.limit_price,
        o.executed_price,
        o.status,
        o.placed_at,
        o.executed_at
    FROM dbo.Orders o
    JOIN dbo.Users u ON u.user_id = o.user_id
    JOIN dbo.Instruments i ON i.instrument_id = o.instrument_id
    WHERE u.phone_number = @phone_number
    ORDER BY o.placed_at DESC;
END;
GO

PRINT 'Stored procedures created successfully.';
GO
