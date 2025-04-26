-- 创建创建表的函数
CREATE OR REPLACE FUNCTION create_tables()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    -- 创建交易记录表
    CREATE TABLE IF NOT EXISTS trades (
        id BIGSERIAL PRIMARY KEY,
        date TEXT NOT NULL,
        stock_code TEXT NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        quantity INTEGER NOT NULL,
        trade_type TEXT NOT NULL CHECK (trade_type IN ('buy', 'sell')),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- 创建个人信息表
    CREATE TABLE IF NOT EXISTS trader_profiles (
        id BIGSERIAL PRIMARY KEY,
        user_id TEXT NOT NULL UNIQUE,
        full_name TEXT,
        professional_title TEXT,
        signature TEXT,
        bio TEXT,
        profile_image_url TEXT,
        trading_experience_years INTEGER,
        specialization TEXT[],
        social_links JSONB,
        contact_info JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- 创建头像历史记录表
    CREATE TABLE IF NOT EXISTS avatar_history (
        id BIGSERIAL PRIMARY KEY,
        user_id TEXT NOT NULL,
        image_url TEXT NOT NULL,
        storage_path TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        mime_type TEXT NOT NULL,
        upload_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        is_current BOOLEAN DEFAULT false,
        FOREIGN KEY (user_id) REFERENCES trader_profiles(user_id)
    );

    -- 创建索引以提高查询性能
    CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(date);
    CREATE INDEX IF NOT EXISTS idx_trades_stock_code ON trades(stock_code);
    CREATE INDEX IF NOT EXISTS idx_trades_trade_type ON trades(trade_type);
    CREATE INDEX IF NOT EXISTS idx_trader_profiles_user_id ON trader_profiles(user_id);
    CREATE INDEX IF NOT EXISTS idx_avatar_history_user_id ON avatar_history(user_id);
    CREATE INDEX IF NOT EXISTS idx_avatar_history_is_current ON avatar_history(is_current);
END;
$$; 