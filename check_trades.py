from supabase import create_client
import os

# Supabase 配置
SUPABASE_URL = "https://rwlziuinlbazgoajkcme.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ3bHppdWlubGJhemdvYWprY21lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxODAwNjIsImV4cCI6MjA2MDc1NjA2Mn0.Y1KiIiUXmDiDSFYFQLHmyd1Oe86SxSfvHJcKrJmz2gI"

# 创建 Supabase 客户端
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 查询 trades1 表
response = supabase.table('trades1').select('*').execute()

# 打印结果
print("Trades1 表数据:")
for trade in response.data:
    print(f"ID: {trade['id']}")
    print(f"股票代码: {trade['symbol']}")
    print(f"买入价格: {trade['entry_price']}")
    print(f"买入日期: {trade['entry_date']}")
    print(f"交易数量: {trade['size']}")
    print(f"卖出价格: {trade['exit_price']}")
    print(f"卖出日期: {trade['exit_date']}")
    print(f"当前价格: {trade['current_price']}")
    print("-" * 50) 