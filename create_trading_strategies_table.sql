-- 创建交易策略表
CREATE TABLE IF NOT EXISTS trading_strategies (
    id BIGSERIAL PRIMARY KEY,
    market_analysis TEXT NOT NULL,           -- 市场分析
    trading_focus TEXT[] NOT NULL,           -- 重点关注股票列表
    risk_warning TEXT NOT NULL,              -- 风险提示
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP   -- 更新时间
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_trading_strategies_updated_at ON trading_strategies(updated_at); 