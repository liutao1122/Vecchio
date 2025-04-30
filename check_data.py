from supabase import create_client
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化 Supabase 客户端
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key)

# 查询所有交易数据
response = supabase.table('trades').select('*').execute()
trades = response.data

print('\n=== 数据库原始数据 ===')
print(f'总交易数: {len(trades)}')
print('\n=== 持仓中的交易 ===')
holding_trades = [t for t in trades if t.get('exit_date') is None]
print(f'持仓数量: {len(holding_trades)}')
for trade in holding_trades:
    print(f"\nSymbol: {trade.get('symbol')}")
    print(f"Entry Date: {trade.get('entry_date')}")
    print(f"Entry Price: {trade.get('entry_price')}")
    print(f"Current Price: {trade.get('current_price')}")
    print(f"Size: {trade.get('size')}")

print('\n=== 已平仓的交易 ===')
closed_trades = [t for t in trades if t.get('exit_date') is not None]
print(f'已平仓数量: {len(closed_trades)}')
for trade in closed_trades:
    print(f"\nSymbol: {trade.get('symbol')}")
    print(f"Entry Date: {trade.get('entry_date')}")
    print(f"Exit Date: {trade.get('exit_date')}")
    print(f"Entry Price: {trade.get('entry_price')}")
    print(f"Exit Price: {trade.get('exit_price')}")
    print(f"Size: {trade.get('size')}")

# 检查数据格式
print('\n=== 数据格式检查 ===')
for trade in trades:
    print(f"\nSymbol: {trade.get('symbol')}")
    print(f"数据类型检查:")
    print(f"  exit_date: {type(trade.get('exit_date'))}")
    print(f"  entry_price: {type(trade.get('entry_price'))}")
    print(f"  exit_price: {type(trade.get('exit_price'))}")
    print(f"  current_price: {type(trade.get('current_price'))}")
    print(f"  size: {type(trade.get('size'))}") 