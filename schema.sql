-- 创建交易员表
CREATE TABLE traders (
    id SERIAL PRIMARY KEY,
    trader_name VARCHAR(100) NOT NULL,
    professional_title VARCHAR(100) NOT NULL,
    profile_image_url TEXT NOT NULL,
    total_profit DECIMAL(15,2) NOT NULL DEFAULT 0,
    total_trades INTEGER NOT NULL DEFAULT 0,
    win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    followers_count INTEGER NOT NULL DEFAULT 0,
    likes_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 插入示例数据
INSERT INTO traders (
    trader_name, 
    professional_title, 
    profile_image_url, 
    total_profit, 
    total_trades, 
    win_rate, 
    followers_count, 
    likes_count
) VALUES 
    (
        'Kathy Wilson',
        'Senior Forex Trader',
        'https://example.com/avatars/kathy.jpg',
        258432.50,
        1250,
        92.5,
        4521,
        15678
    ),
    (
        'Michael Chen',
        'Crypto Expert',
        'https://example.com/avatars/michael.jpg',
        198756.75,
        986,
        88.3,
        3876,
        12543
    ),
    (
        'Sarah Johnson',
        'Stock Market Analyst',
        'https://example.com/avatars/sarah.jpg',
        175890.25,
        875,
        85.7,
        3254,
        10987
    ),
    (
        'David Brown',
        'Technical Analyst',
        'https://example.com/avatars/david.jpg',
        145670.80,
        756,
        83.2,
        2987,
        9876
    ),
    (
        'Emma Davis',
        'Value Hunter',
        'https://example.com/avatars/emma.jpg',
        132450.60,
        645,
        81.5,
        2654,
        8765
    ),
    (
        'James Wilson',
        'Swing Trader',
        'https://example.com/avatars/james.jpg',
        128760.40,
        589,
        79.8,
        2432,
        7654
    ),
    (
        'Lisa Zhang',
        'Day Trader',
        'https://example.com/avatars/lisa.jpg',
        115890.30,
        534,
        78.4,
        2198,
        6543
    ),
    (
        'Robert Taylor',
        'Options Specialist',
        'https://example.com/avatars/robert.jpg',
        98760.25,
        478,
        76.9,
        1987,
        5432
    ),
    (
        'Anna Martinez',
        'Market Strategist',
        'https://example.com/avatars/anna.jpg',
        87650.15,
        423,
        75.3,
        1765,
        4321
    ),
    (
        'Thomas Anderson',
        'Portfolio Manager',
        'https://example.com/avatars/thomas.jpg',
        76540.90,
        367,
        73.8,
        1543,
        3210
    );

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_traders_updated_at
    BEFORE UPDATE ON traders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 