-- 启用 RLS
ALTER TABLE trading_strategies ENABLE ROW LEVEL SECURITY;

-- 创建策略允许匿名用户读取数据
CREATE POLICY "允许匿名读取交易策略" ON trading_strategies
    FOR SELECT
    TO anon
    USING (true);

-- 创建策略允许已认证用户进行所有操作
CREATE POLICY "允许认证用户完全访问" ON trading_strategies
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true); 