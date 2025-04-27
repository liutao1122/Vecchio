-- 添加image_url字段到trades表
ALTER TABLE trades ADD COLUMN IF NOT EXISTS image_url TEXT; 