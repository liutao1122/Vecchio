-- 更新交易状态值
UPDATE trades SET status = '以止盈' WHERE status = '已止盈';
UPDATE trades SET status = '以止损' WHERE status = '已止损';

-- 修改表结构中的状态约束
ALTER TABLE trades DROP CONSTRAINT IF EXISTS trades_status_check;
ALTER TABLE trades ADD CONSTRAINT trades_status_check CHECK (status IN ('持有中', '以止盈', '以止损')); 