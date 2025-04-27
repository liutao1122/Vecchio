-- 创建交易记录表
CREATE TABLE IF NOT EXISTS trades (
    -- 主键和基本信息
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,                    -- 股票代码
    trade_type TEXT NOT NULL CHECK (trade_type IN ('buy', 'sell')),  -- 交易类型：买入/卖出
    status TEXT NOT NULL CHECK (status IN ('持有中', '已平仓')),      -- 交易状态
    
    -- 交易详情
    entry_price DECIMAL(10,2) NOT NULL,      -- 入场价格
    entry_quantity INTEGER NOT NULL,         -- 入场数量
    entry_amount DECIMAL(15,2) NOT NULL,     -- 入场金额
    entry_date TIMESTAMP WITH TIME ZONE NOT NULL,  -- 入场时间
    
    -- 平仓信息（如果已平仓）
    exit_price DECIMAL(10,2),                -- 出场价格
    exit_quantity INTEGER,                   -- 出场数量
    exit_amount DECIMAL(15,2),               -- 出场金额
    exit_date TIMESTAMP WITH TIME ZONE,      -- 出场时间
    
    -- 当前状态
    current_price DECIMAL(10,2),             -- 当前价格
    current_amount DECIMAL(15,2),            -- 当前金额
    profit_amount DECIMAL(15,2),             -- 盈利金额
    profit_ratio DECIMAL(10,2),              -- 盈利比例
    
    -- 其他信息
    notes TEXT,                              -- 备注
    image_url TEXT,                          -- 股票图片URL
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP   -- 更新时间
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_entry_date ON trades(entry_date);
CREATE INDEX IF NOT EXISTS idx_trades_exit_date ON trades(exit_date); 