from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response
from supabase import create_client
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz
import hashlib
import json
import os
import uuid
import random
import sqlite3
import requests
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from werkzeug.utils import secure_filename
import supabase_client  # 用 supabase_client.get_traders 代替

# Flask应用配置
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_secret_key_here')
CORS(app, supports_credentials=True)

# Supabase配置
url = 'https://rwlziuinlbazgoajkcme.supabase.co'
key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ3bHppdWlubGJhemdvYWprY21lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NTE4MDA2MiwiZXhwIjoyMDYwNzU2MDYyfQ.HAAXKlwasbIoq27IHRUn4gZoMfzGvUfsI4pt4NqCThk'
supabase = create_client(url, key)

# 股票图片映射
STOCK_IMAGES = {
    'AAPL': 'https://logo.clearbit.com/apple.com',
    'MSFT': 'https://logo.clearbit.com/microsoft.com',
    'GOOGL': 'https://logo.clearbit.com/google.com',
    'AMZN': 'https://logo.clearbit.com/amazon.com',
    'META': 'https://logo.clearbit.com/meta.com',
    'TSLA': 'https://logo.clearbit.com/tesla.com',
    'NVDA': 'https://logo.clearbit.com/nvidia.com',
    'JPM': 'https://logo.clearbit.com/jpmorgan.com',
    'V': 'https://logo.clearbit.com/visa.com',
    'WMT': 'https://logo.clearbit.com/walmart.com'
}

# 数据库配置
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'trading_platform'
}

# 数据库连接函数
def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def format_datetime(dt_str):
    """将UTC时间字符串转换为美国东部时间并格式化为 DD-MMM-YY 格式"""
    try:
        # 解析UTC时间字符串
        dt = datetime.strptime(dt_str.split('+')[0], '%Y-%m-%d %H:%M:%S.%f')
        # 设置为UTC时区
        dt = pytz.UTC.localize(dt)
        # 转换为美国东部时间
        eastern = pytz.timezone('America/New_York')
        dt = dt.astimezone(eastern)
        # 格式化为 DD-MMM-YY 格式 (Windows 兼容格式)
        day = str(dt.day)  # 不使用 %-d
        return f"{day}-{dt.strftime('%b-%y')}"
    except Exception as e:
        try:
            # 尝试其他格式
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            dt = pytz.UTC.localize(dt)
            eastern = pytz.timezone('America/New_York')
            dt = dt.astimezone(eastern)
            day = str(dt.day)  # 不使用 %-d
            return f"{day}-{dt.strftime('%b-%y')}"
        except:
            return dt_str

def format_date_for_db(dt):
    """将日期格式化为数据库存储格式（UTC）"""
    if isinstance(dt, str):
        try:
            # 尝试解析 DD-MMM-YY 格式
            dt = datetime.strptime(dt, '%d-%b-%y')
        except:
            return dt
    # 确保时区是UTC
    if dt.tzinfo is None:
        eastern = pytz.timezone('America/New_York')
        dt = eastern.localize(dt)
    return dt.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S.%f+00:00')

def get_real_time_price(symbol):
    """获取股票实时价格"""
    try:
        api_key = "E7pSY5mZfHuHtXsDmbk8TORK_XHN6ffq"
        # 使用实时数据端点
        url = f"https://api.polygon.io/v2/last/trade/{symbol}?apiKey={api_key}"
        print(f"\n=== 开始获取 {symbol} 的实时价格 ===")
        print(f"请求URL: {url}")
        
        response = requests.get(url)
        print(f"响应状态码: {response.status_code}")
        print(f"完整响应内容: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"解析后的JSON数据: {data}")
            
            if data.get('results'):
                price = float(data['results']['p'])  # 使用最新成交价
                print(f"成功获取 {symbol} 的实时价格: {price}")
                return price
            else:
                print(f"在响应中未找到价格数据: {data}")
        elif response.status_code == 403:
            print(f"API权限错误，请检查API密钥权限")
        else:
            print(f"API请求失败，状态码: {response.status_code}")
        return None
    except Exception as e:
        print(f"获取 {symbol} 价格时发生错误: {str(e)}")
        return None

def get_historical_data(symbol):
    """获取历史数据"""
    try:
        stock = yf.Ticker(symbol)
        history = stock.history(period="1mo")  # 获取一个月的历史数据
        if not history.empty:
            # 将数据转换为列表格式
            data = []
            for date, row in history.iterrows():
                data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume'])
                })
            return data
        return None
    except Exception as e:
        print(f"Error getting historical data for {symbol}: {str(e)}")
        return None

def get_device_fingerprint():
    """生成设备指纹"""
    user_agent = request.headers.get('User-Agent', '')
    ip = request.remote_addr
    # 可以添加更多设备特征
    fingerprint_data = f"{ip}:{user_agent}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()

def get_next_whatsapp_agent(device_fingerprint):
    """获取下一个可用的WhatsApp客服"""
    try:
        print("开始获取WhatsApp客服")
        print(f"使用设备指纹: {device_fingerprint}")
        
        # 测试数据库连接
        try:
            test_query = supabase.table('whatsapp_agents').select('count').execute()
            print(f"数据库连接测试: {test_query.data}")
        except Exception as db_error:
            print(f"数据库连接测试失败: {str(db_error)}")
            return None
        
        # 检查是否已有分配记录
        try:
            existing_record = supabase.table('contact_records').select('*').eq('device_fingerprint', device_fingerprint).execute()
            print(f"现有记录查询结果: {existing_record.data}")
        except Exception as e:
            print(f"查询现有记录失败: {str(e)}")
            return None
        
        if existing_record.data:
            # 如果已有分配，返回之前分配的客服
            agent_id = existing_record.data[0]['agent_id']
            print(f"找到现有分配的客服ID: {agent_id}")
            try:
                agent = supabase.table('whatsapp_agents').select('*').eq('id', agent_id).execute()
                print(f"获取到现有客服信息: {agent.data}")
                return agent.data[0] if agent.data else None
            except Exception as e:
                print(f"获取现有客服信息失败: {str(e)}")
                return None
        
        # 获取所有客服
        try:
            agents = supabase.table('whatsapp_agents').select('*').eq('is_active', True).execute()
            print(f"可用客服列表查询结果: {agents.data}")
            if not agents.data:
                print("没有找到可用的客服")
                return None
        except Exception as e:
            print(f"获取客服列表失败: {str(e)}")
            return None
            
        # 获取每个客服的当前分配数量
        try:
            assignments = supabase.table('contact_records').select('agent_id, count').execute()
            print(f"客服分配记录查询结果: {assignments.data}")
            assignment_counts = {}
            for record in assignments.data:
                agent_id = record['agent_id']
                assignment_counts[agent_id] = assignment_counts.get(agent_id, 0) + 1
            print(f"客服分配数量统计: {assignment_counts}")
        except Exception as e:
            print(f"获取分配记录失败: {str(e)}")
            assignment_counts = {}
            
        # 选择分配数量最少的客服
        min_assignments = float('inf')
        selected_agent = None
        
        for agent in agents.data:
            count = assignment_counts.get(agent['id'], 0)
            if count < min_assignments:
                min_assignments = count
                selected_agent = agent
        
        print(f"选择的客服: {selected_agent}")
        
        if selected_agent:
            # 记录新的分配
            try:
                insert_data = {
                    'device_fingerprint': device_fingerprint,
                    'agent_id': selected_agent['id'],
                    'ip_address': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'timestamp': datetime.now(pytz.UTC).isoformat()
                }
                print(f"准备插入新记录: {insert_data}")
                insert_result = supabase.table('contact_records').insert(insert_data).execute()
                print(f"插入记录结果: {insert_result.data}")
            except Exception as e:
                print(f"插入分配记录失败: {str(e)}")
                # 即使插入失败也返回选中的客服
                
        return selected_agent
        
    except Exception as e:
        print(f"获取WhatsApp客服时发生错误: {str(e)}")
        return None

@app.route('/api/get-whatsapp-link', methods=['GET', 'POST'])
def get_whatsapp_link():
    """获取WhatsApp链接API"""
    try:
        print("\n=== 开始处理WhatsApp链接请求 ===")
        device_fingerprint = get_device_fingerprint()
        print(f"生成的设备指纹: {device_fingerprint}")
        
        # 获取点击时间
        click_time = None
        if request.method == 'POST':
            data = request.get_json()
            click_time = data.get('click_time')
            print(f"记录点击时间: {click_time}")
        
        agent = get_next_whatsapp_agent(device_fingerprint)
        print(f"获取到的客服信息: {agent}")
        
        if agent:
            # 更新点击时间
            if click_time:
                try:
                    update_data = {
                        'click_time': click_time
                    }
                    update_result = supabase.table('contact_records').update(update_data).eq('device_fingerprint', device_fingerprint).execute()
                    print(f"更新点击时间结果: {update_result.data}")
                except Exception as e:
                    print(f"更新点击时间失败: {str(e)}")
            
            app_link = f"whatsapp://send?phone={agent['phone_number']}"
            print(f"生成的WhatsApp链接: {app_link}")
            return {
                'success': True,
                'app_link': app_link
            }
        else:
            print("未能获取到可用的客服")
            return {
                'success': False,
                'message': "No available support agent, please try again later"
            }
            
    except Exception as e:
        print(f"处理WhatsApp链接请求时发生错误: {str(e)}")
        return {
            'success': False,
            'message': "System error, please try again later"
        }

@app.route('/')
def index():
    try:
        # 获取交易数据
        response = supabase.table('trades1').select("*").execute()
        trades = response.data

        if not trades:
            print("No trades found in database")
            trades = []
        
        print("\n=== 原始数据 ===")
        for trade in trades:
            print(f"Symbol: {trade['symbol']}")
            print(f"Entry Date: {trade.get('entry_date')}")
            print(f"Exit Date: {trade.get('exit_date')}")
            print("---")
        
        # 为每个交易添加图片URL和计算属性
        for trade in trades:
            # 格式化日期前先保存原始日期用于排序
            if trade.get('exit_date'):
                # 将日期字符串转换为datetime对象用于排序
                try:
                    # 尝试解析数据库中的日期格式
                    exit_date = datetime.strptime(trade['exit_date'].split('+')[0], '%Y-%m-%d %H:%M:%S.%f')
                    trade['original_exit_date'] = exit_date
                    print(f"\nExit date for {trade['symbol']}:")
                    print(f"Original string: {trade['exit_date']}")
                    print(f"Parsed datetime: {exit_date}")
                except Exception as e:
                    print(f"\nError parsing exit date for {trade['symbol']}:")
                    print(f"Date string: {trade['exit_date']}")
                    print(f"Error: {e}")
                    # 如果解析失败，尝试其他格式
                    try:
                        exit_date = datetime.fromisoformat(trade['exit_date'].replace('Z', '+00:00'))
                        trade['original_exit_date'] = exit_date
                        print(f"Successfully parsed using ISO format: {exit_date}")
                    except Exception as e2:
                        print(f"Second parsing attempt failed: {e2}")
                        trade['original_exit_date'] = datetime.min
                trade['exit_date'] = format_datetime(trade['exit_date'])

            if trade.get('entry_date'):
                try:
                    entry_date = datetime.strptime(trade['entry_date'].split('+')[0], '%Y-%m-%d %H:%M:%S.%f')
                    trade['original_entry_date'] = entry_date
                except Exception as e:
                    try:
                        entry_date = datetime.fromisoformat(trade['entry_date'].replace('Z', '+00:00'))
                        trade['original_entry_date'] = entry_date
                    except:
                        trade['original_entry_date'] = datetime.min
                trade['entry_date'] = format_datetime(trade['entry_date'])
            
            # 优先使用数据库中的 image_url，否则用 STOCK_IMAGES
            trade['image_url'] = trade.get('image_url') or STOCK_IMAGES.get(trade['symbol'], '')
            
            # 计算交易金额和盈亏
            trade['entry_amount'] = trade['entry_price'] * trade['size']
            
            # 如果没有current_price，获取实时价格
            if 'current_price' not in trade or not trade['current_price']:
                current_price = get_real_time_price(trade['symbol'])
                if current_price:
                    trade['current_price'] = current_price
                    # 更新数据库中的价格
                    print(f"\n=== 更新数据库中的价格 ===")
                    print(f"交易ID: {trade['id']}")
                    print(f"股票代码: {trade['symbol']}")
                    print(f"新价格: {current_price}")
                    try:
                        update_response = supabase.table('trades1').update({
                            'current_price': current_price,
                            'updated_at': datetime.now(pytz.UTC).isoformat()
                        }).eq('id', trade['id']).execute()
                        print(f"数据库更新响应: {update_response.data}")
                    except Exception as e:
                        print(f"更新数据库时发生错误: {str(e)}")
            
            # 计算当前市值和盈亏
            trade['current_amount'] = trade['current_price'] * trade['size'] if trade.get('current_price') else trade['entry_amount']
            
            # 计算盈亏
            if trade.get('exit_price'):
                trade['profit_amount'] = (trade['exit_price'] - trade['entry_price']) * trade['size']
            else:
                trade['profit_amount'] = (trade['current_price'] - trade['entry_price']) * trade['size'] if trade.get('current_price') else 0
            
            # 计算盈亏比例
            trade['profit_ratio'] = (trade['profit_amount'] / trade['entry_amount']) * 100 if trade['entry_amount'] else 0
            
            # 设置状态
            if trade.get('exit_price') is None and trade.get('exit_date') is None:
                trade['status'] = "Active"
            else:
                trade['status'] = "Closed"
        
        # 分离持仓和平仓的交易
        holding_trades = [t for t in trades if t['status'] == "Active"]
        closed_trades = [t for t in trades if t['status'] == "Closed"]

        print("\n=== 排序前的交易 ===")
        print("持仓中的交易:")
        for trade in holding_trades:
            print(f"Symbol: {trade['symbol']}")
            print(f"Entry Date: {trade.get('entry_date')}")
            print(f"Original Entry Date: {trade.get('original_entry_date')}")
            print("---")
        
        print("\n平仓的交易:")
        for trade in closed_trades:
            print(f"Symbol: {trade['symbol']}")
            print(f"Exit Date: {trade.get('exit_date')}")
            print(f"Original Exit Date: {trade.get('original_exit_date')}")
            print("---")
        
        # 对持仓交易按买入时间降序排序（最近的在前面）
        holding_trades.sort(key=lambda x: x['original_entry_date'], reverse=True)
        
        # 对平仓交易按退出时间降序排序
        closed_trades.sort(key=lambda x: x['original_exit_date'], reverse=True)
        
        print("\n=== 排序后的交易 ===")
        print("持仓中的交易:")
        for trade in holding_trades:
            print(f"Symbol: {trade['symbol']}")
            print(f"Entry Date: {trade.get('entry_date')}")
            print(f"Original Entry Date: {trade.get('original_entry_date')}")
            print("---")
        
        print("\n平仓的交易:")
        for trade in closed_trades:
            print(f"Symbol: {trade['symbol']}")
            print(f"Exit Date: {trade.get('exit_date')}")
            print(f"Original Exit Date: {trade.get('original_exit_date')}")
            print("---")
        
        # 合并排序后的交易列表
        sorted_trades = holding_trades + closed_trades
        
        print("\n=== 最终排序后的交易列表 ===")
        print("持仓中的交易:")
        for trade in [t for t in sorted_trades if t['status'] == "Active"]:
            print(f"Symbol: {trade['symbol']}")
            print(f"Entry Date: {trade.get('entry_date')}")
            print(f"Original Entry Date: {trade.get('original_entry_date')}")
            print("---")
        
        print("\n平仓的交易:")
        for trade in [t for t in sorted_trades if t['status'] == "Closed"]:
            print(f"Symbol: {trade['symbol']}")
            print(f"Exit Date: {trade.get('exit_date')}")
            print(f"Original Exit Date: {trade.get('original_exit_date')}")
            print("---")
        
        # 计算总览数据
        total_trades = len(sorted_trades)
        
        # 获取当前持仓
        positions = holding_trades
        
        # 获取当前美国东部时间的月份
        eastern = pytz.timezone('America/New_York')
        current_time = datetime.now(eastern)
        current_month = f"{str(current_time.day)}-{current_time.strftime('%b-%y')}"
        
        # 计算当月平仓盈亏
        monthly_closed_trades = [t for t in closed_trades 
                               if t.get('exit_date') 
                               and t['exit_date'].split('-')[1] == current_month.split('-')[1]]
        
        monthly_profit = sum(t.get('profit_amount', 0) for t in monthly_closed_trades)

        # 获取交易员信息
        profile_response = supabase.table('trader_profiles').select("*").limit(1).execute()
        trader_info = profile_response.data[0] if profile_response.data else {
            'trader_name': 'Professional Trader',
            'professional_title': 'Financial Trading Expert | Technical Analysis Master',
            'bio': 'Focused on US stock market technical analysis and quantitative trading',
            'profile_image_url': 'https://rwlziuinlbazgoajkcme.supabase.co/storage/v1/object/public/images/1920134_331262340400234_2042663349514343562_n.jpg'
        }
        
        # 获取最新的交易策略
        strategy_response = supabase.table('trading_strategies').select("*").order('updated_at', desc=True).limit(1).execute()
        strategy_info = strategy_response.data[0] if strategy_response.data else {
            'market_analysis': 'Today\'s market shows an upward trend with strong performance in the tech sector. Focus on AI-related stocks...',
            'trading_focus': ['Tech Sector: AI, Chips, Cloud Computing', 'New Energy: Solar, Energy Storage, Hydrogen', 'Healthcare: Innovative Drugs, Medical Devices'],
            'risk_warning': 'High market volatility, please control position size and set stop loss...',
            'updated_at': datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S.%f+00:00')
        }
        
        # 格式化更新时间
        if strategy_info.get('updated_at'):
            strategy_info['formatted_time'] = format_datetime(strategy_info['updated_at'])
        
        # 计算总利润
        total_profit = sum(t.get('profit_amount', 0) for t in sorted_trades)

        # 设置个人信息
        trader_info = {
            'trader_name': trader_info.get('trader_name', 'Professional Trader'),
            'professional_title': trader_info.get('professional_title', 'Financial Trading Expert | Technical Analysis Master'),
            'bio': trader_info.get('bio', 'Focused on US stock market technical analysis and quantitative trading'),
            'positions': positions,
            'monthly_profit': round(monthly_profit, 2),
            'active_trades': len(positions),
            'total_profit': round(total_profit, 2),
            'strategy_info': strategy_info,
            'profile_image_url': trader_info.get('profile_image_url')
        }
        
        return render_template('index.html', 
                            trades=sorted_trades,
                            trader_info=trader_info)
    except Exception as e:
        print(f"Error in index route: {e}")
        return render_template('index.html', 
                            trades=[],
                            trader_info={
                                'trader_name': 'System Error', 
                                'monthly_profit': 0, 
                                'active_trades': 0,
                                'total_profit': 0
                            })

@app.route('/api/trader-profile', methods=['GET'])
def trader_profile():
    try:
        # 获取个人资料
        response = supabase.table('trader_profiles').select('*').limit(1).execute()
        
        # 获取trades表中的记录数
        trades_response = supabase.table('trades1').select('id').execute()
        trades_count = len(trades_response.data) if trades_response.data else 0
        
        if response.data:
            profile = response.data[0]
            # 更新总交易次数 = trader_profiles表中的total_trades + trades表中的记录数
            profile['total_trades'] = profile.get('total_trades', 0) + trades_count
            return jsonify({
                'success': True,
                'data': profile
            })
        else:
            # 如果没有数据，返回默认值
            return jsonify({
                'success': True,
                'data': {
                    'trader_name': 'Professional Trader',
                    'professional_title': 'Stock Trading Expert | Technical Analysis Master',
                    'years_of_experience': 5,
                    'total_trades': trades_count,
                    'win_rate': 85.0
                }
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/leaderboard')
def leaderboard():
    # Get sort parameter from query string, default to 'profit'
    sort_by = request.args.get('sort', 'profit')
    # Get traders from Supabase
    traders = supabase_client.get_traders(sort_by)
    # If no traders found, return empty list
    if not traders:
        traders = []
    return render_template('leaderboard.html', traders=traders)

@app.route('/api/upload-avatar', methods=['POST'])
def upload_avatar():
    try:
        if 'avatar' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400

        file = request.files['avatar']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        # 检查文件类型
        if not file.type.startswith('image/'):
            return jsonify({'success': False, 'message': 'Please upload an image file'}), 400

        # 获取文件信息
        file_size = len(file.read())
        file.seek(0)  # 重置文件指针
        
        # 检查文件大小（限制为5MB）
        if file_size > 5 * 1024 * 1024:
            return jsonify({'success': False, 'message': 'File size cannot exceed 5MB'}), 400

        # 生成唯一的文件名
        file_extension = os.path.splitext(file.filename)[1].lower()
        unique_filename = f"avatars/{str(uuid.uuid4())}{file_extension}"

        # 上传到Supabase存储
        file_bytes = file.read()
        # 修正调用方式，兼容本地 supabase-py 版本
        result = supabase.storage().from_('avatars').upload(
            unique_filename,
            file_bytes,
            file_options={"content-type": file.content_type}
        )
        # 获取图片URL
        file_url = supabase.storage().from_('avatars').get_public_url(unique_filename)
        # 更新trades1表
        supabase.table('trades1').update({'image_url': file_url}).eq('id', trade_id).execute()

        # 获取第一个交易员的ID（因为目前是单用户系统）
        profile_response = supabase.table('trader_profiles').select('id').limit(1).execute()
        if not profile_response.data:
            # 如果没有找到交易员记录，创建一个新记录
            eastern = pytz.timezone('America/New_York')
            current_time = datetime.now(eastern)
            trader_data = {
                'trader_name': 'Professional Trader',
                'professional_title': 'Financial Trading Expert',
                'created_at': format_date_for_db(current_time),
                'updated_at': format_date_for_db(current_time)
            }
            profile_response = supabase.table('trader_profiles').insert(trader_data).execute()
        
        trader_id = profile_response.data[0]['id']

        # 将之前的头像标记为非当前
        supabase.table('avatar_history').update({
            'is_current': False
        }).eq('user_id', trader_id).execute()

        # 插入新的头像记录
        eastern = pytz.timezone('America/New_York')
        current_time = datetime.now(eastern)
        avatar_data = {
            'user_id': trader_id,
            'image_url': file_url,
            'storage_path': unique_filename,
            'file_name': file.filename,
            'file_size': file_size,
            'mime_type': file.content_type,
            'is_current': True,
            'created_at': format_date_for_db(current_time)
        }
        supabase.table('avatar_history').insert(avatar_data).execute()

        # 更新用户个人资料
        supabase.table('trader_profiles').update({
            'profile_image_url': file_url,
            'updated_at': format_date_for_db(current_time)
        }).eq('id', trader_id).execute()

        return jsonify({
            'success': True,
            'url': file_url
        })

    except Exception as e:
        print(f"Upload failed: {str(e)}")
        return jsonify({'success': False, 'message': 'Upload failed, please try again later'}), 500

@app.route('/api/get-avatar', methods=['GET'])
def get_avatar():
    try:
        # 获取当前交易员的头像URL
        profile_response = supabase.table('trader_profiles').select('profile_image_url').limit(1).execute()
        if profile_response.data:
            return jsonify({
                'success': True,
                'url': profile_response.data[0]['profile_image_url']
            })
        return jsonify({
            'success': False,
            'message': 'Avatar not found'
        })
    except Exception as e:
        print(f"Failed to get avatar: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to get avatar'
        }), 500

@app.route('/api/price')
def api_price():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({'success': False, 'message': 'No symbol provided'}), 400

    price = get_real_time_price(symbol)
    if price is not None:
        return jsonify({'success': True, 'price': float(price)})
    else:
        return jsonify({'success': False, 'message': 'Failed to get price'}), 500

@app.route('/api/history')
def api_history():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({'success': False, 'message': 'No symbol provided'}), 400

    history = get_historical_data(symbol)
    if history is not None:
        return jsonify({'success': True, 'data': history})
    else:
        return jsonify({'success': False, 'message': 'Failed to get historical data'}), 500

@app.route('/vip')
def vip():
    if 'username' in session:
        # 从Supabase获取用户信息
        response = supabase.table('users').select('*').eq('username', session['username']).execute()
        
        if response.data:
            user = response.data[0]
            trader_info = {
                'trader_name': user['username'],
                'membership_level': user.get('membership_level', 'VIP Member'),
                'trading_volume': user.get('trading_volume', 0),
                'profile_image_url': 'https://via.placeholder.com/180'
            }
        else:
            trader_info = {
                'trader_name': session['username'],
                'membership_level': 'VIP Member',
                'trading_volume': 0,
                'profile_image_url': 'https://via.placeholder.com/180'
            }
    else:
        # 未登录用户的默认信息
        trader_info = {
            'membership_level': 'VIP Member',
            'trading_volume': 0,
            'profile_image_url': 'https://via.placeholder.com/180'
        }
            
    return render_template('vip.html', trader_info=trader_info)

# --- 用户表自动建表 ---
def init_user_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE,
            status TEXT DEFAULT 'active',
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            last_login_ip TEXT,
            last_login_location TEXT,
            membership_level TEXT DEFAULT '普通会员'
        )
    ''')
    conn.commit()
    conn.close()

# --- 会员等级表自动建表 ---
def init_membership_levels_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS membership_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            level INTEGER NOT NULL,
            min_trading_volume DECIMAL(10,2) NOT NULL,
            benefits TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 插入默认会员等级
    default_levels = [
        ('普通会员', 1, 0.00, '基础交易工具,标准市场分析,社区访问,标准支持'),
        ('黄金会员', 2, 100000.00, '高级交易工具,实时市场分析,优先支持,VIP社区访问,交易策略分享'),
        ('钻石会员', 3, 500000.00, '所有黄金会员权益,个人交易顾问,定制策略开发,新功能优先体验,专属交易活动'),
        ('至尊黑卡', 4, 1000000.00, '所有钻石会员权益,24/7专属交易顾问,AI量化策略定制,全球金融峰会邀请,专属投资机会,一对一交易指导')
    ]
    
    c.execute('SELECT COUNT(*) FROM membership_levels')
    if c.fetchone()[0] == 0:
        c.executemany('''
            INSERT INTO membership_levels (name, level, min_trading_volume, benefits)
            VALUES (?, ?, ?, ?)
        ''', default_levels)
    
    conn.commit()
    conn.close()

# --- 用户会员等级关联表自动建表 ---
def init_user_membership_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_membership (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            level_id INTEGER NOT NULL,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (level_id) REFERENCES membership_levels (id)
        )
    ''')
    conn.commit()
    conn.close()

# --- 会员等级分配API ---
@app.route('/api/admin/assign-membership', methods=['POST'])
def assign_membership():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            print("权限检查失败：不是管理员")
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        data = request.get_json()
        if not data.get('user_id'):
            print("缺少用户ID")
            return jsonify({'success': False, 'message': '缺少用户ID'}), 400

        # 根据level_id获取会员等级名称
        membership_levels = {
            '1': '普通会员',
            '2': '黄金会员',
            '3': '钻石会员',
            '4': '至尊黑卡'
        }
        
        level_name = membership_levels.get(str(data.get('level_id')))
        if not level_name:
            print(f"无效的会员等级ID: {data.get('level_id')}")
            return jsonify({'success': False, 'message': '无效的会员等级'}), 400

        print(f"准备更新用户 {data['user_id']} 的会员等级为 {level_name}")
        
        # 直接更新users表
        response = supabase.table('users').update({
            'membership_level': level_name
        }).eq('id', data['user_id']).execute()
        
        if not response.data:
            print("更新失败，未找到用户")
            return jsonify({'success': False, 'message': '用户不存在'}), 404
            
        print("会员等级更新成功")
        return jsonify({'success': True, 'message': '会员等级分配成功'})
        
    except Exception as e:
        print(f"分配会员等级时发生错误: {str(e)}")
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'}), 500

# --- 获取用户会员等级信息 ---
@app.route('/api/user/membership', methods=['GET'])
def get_user_membership():
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '请先登录'}), 401
            
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # 获取用户的会员等级信息
        c.execute('''
            SELECT m.name, m.level, m.benefits
            FROM user_membership um
            JOIN membership_levels m ON um.level_id = m.id
            WHERE um.user_id = ?
        ''', (session['user_id'],))
        
        membership = c.fetchone()
        conn.close()
        
        if membership:
            return jsonify({
                'success': True,
                'membership': {
                    'name': membership[0],
                    'level': membership[1],
                    'benefits': membership[2]
                }
            })
        else:
            return jsonify({
                'success': True,
                'membership': None
            })
            
    except Exception as e:
        print(f"Get user membership error: {str(e)}")
        return jsonify({'success': False, 'message': '获取会员信息失败'}), 500

# --- 会员等级管理API ---
@app.route('/api/admin/membership-levels', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_membership_levels():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        if request.method == 'GET':
            # 获取所有会员等级
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('SELECT * FROM membership_levels ORDER BY level')
            levels = []
            for row in c.fetchall():
                levels.append({
                    'id': row[0],
                    'name': row[1],
                    'level': row[2],
                    'min_trading_volume': row[3],
                    'benefits': row[4],
                    'created_at': row[5]
                })
            conn.close()
            return jsonify({'success': True, 'levels': levels})
            
        elif request.method == 'POST':
            # 创建新会员等级
            data = request.get_json()
            required_fields = ['name', 'level', 'min_trading_volume', 'benefits']
            
            if not all(field in data for field in required_fields):
                return jsonify({'success': False, 'message': '缺少必要字段'}), 400
                
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('''
                INSERT INTO membership_levels (name, level, min_trading_volume, benefits)
                VALUES (?, ?, ?, ?)
            ''', (data['name'], data['level'], data['min_trading_volume'], data['benefits']))
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': '会员等级创建成功'})
            
        elif request.method == 'PUT':
            # 更新会员等级
            data = request.get_json()
            required_fields = ['id', 'name', 'level', 'min_trading_volume', 'benefits']
            
            if not all(field in data for field in required_fields):
                return jsonify({'success': False, 'message': '缺少必要字段'}), 400
                
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('''
                UPDATE membership_levels
                SET name = ?, level = ?, min_trading_volume = ?, benefits = ?
                WHERE id = ?
            ''', (data['name'], data['level'], data['min_trading_volume'], data['benefits'], data['id']))
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': '会员等级更新成功'})
            
        elif request.method == 'DELETE':
            # 删除会员等级
            level_id = request.args.get('id')
            if not level_id:
                return jsonify({'success': False, 'message': '缺少会员等级ID'}), 400
                
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('DELETE FROM membership_levels WHERE id = ?', (level_id,))
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': '会员等级删除成功'})
            
    except Exception as e:
        print(f"Manage membership levels error: {str(e)}")
        return jsonify({'success': False, 'message': '操作失败'}), 500

# --- 登录接口（Supabase版） ---
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        # 从Supabase获取用户信息
        response = supabase.table('users').select('*').eq('username', username).execute()
        
        if not response.data:
            return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
            
        user = response.data[0]
        
        # TODO: 在实际应用中应该进行密码验证
        # 这里简化处理，直接验证密码是否匹配
        if password != user.get('password_hash'):  # 实际应用中应该使用proper密码验证
            return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
            
        if user.get('status') != 'active':
            return jsonify({'success': False, 'message': '账号已被禁用'}), 403
            
        # 获取IP和地址信息
        ip_address = request.remote_addr
        try:
            response = requests.get(f'https://ipinfo.io/{ip_address}/json')
            location_data = response.json()
            location = f"{location_data.get('city', '')}, {location_data.get('region', '')}, {location_data.get('country', '')}"
        except:
            location = '未知位置'
            
        # 更新用户登录信息
        supabase.table('users').update({
            'last_login': datetime.now(pytz.UTC).isoformat(),
            'last_login_ip': ip_address,
            'last_login_location': location
        }).eq('id', user['id']).execute()
        
        # 设置session
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user.get('role', 'user')
        
        return jsonify({
            'success': True,
            'message': '登录成功',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'role': user.get('role', 'user'),
                'membership_level': user.get('membership_level', '普通会员')
            }
        })
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({'success': False, 'message': '登录失败'}), 500

# --- 登出接口 ---
@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        # 清除session
        session.clear()
        return jsonify({'success': True, 'message': '已成功登出'})
    except Exception as e:
        print(f"Logout error: {str(e)}")
        return jsonify({'success': False, 'message': '登出失败'}), 500

def update_holding_stocks_prices():
    """更新所有持有中股票的实时价格"""
    try:
        print("\n=== 开始更新持有股票价格 ===")
        # 获取所有持有中的股票
        response = supabase.table('trades1').select("*").execute()
        trades = response.data
        
        if not trades:
            print("No trades found")
            return
        
        print(f"找到 {len(trades)} 条交易记录")
        
        # 遍历每个持有中的股票
        for trade in trades:
            # 检查是否是持有中的股票
            if trade.get('exit_price') is None and trade.get('exit_date') is None:
                symbol = trade['symbol']
                print(f"\n处理股票: {symbol}")
                print(f"交易ID: {trade['id']}")
                print(f"当前价格: {trade.get('current_price')}")
                
                # 获取实时价格
                current_price = get_real_time_price(symbol)
                
                if current_price:
                    print(f"获取到新价格: {current_price}")
                    # 计算新的数据
                    entry_amount = trade['entry_price'] * trade['size']
                    current_amount = current_price * trade['size']
                    profit_amount = current_amount - entry_amount
                    profit_ratio = (profit_amount / entry_amount) * 100 if entry_amount else 0
                    
                    print(f"计算得到:")
                    print(f"入场金额: {entry_amount}")
                    print(f"当前金额: {current_amount}")
                    print(f"盈亏金额: {profit_amount}")
                    print(f"盈亏比例: {profit_ratio}%")
                    
                    try:
                        # 只更新current_price字段
                        update_data = {
                            'current_price': current_price
                        }
                        print(f"准备更新数据: {update_data}")
                        
                        update_response = supabase.table('trades1').update(update_data).eq('id', trade['id']).execute()
                        
                        if update_response.data:
                            print(f"数据库更新成功: {update_response.data}")
                            # 验证更新是否成功
                            verify_response = supabase.table('trades1').select('current_price').eq('id', trade['id']).execute()
                            if verify_response.data:
                                print(f"验证更新后的价格: {verify_response.data[0]['current_price']}")
                        else:
                            print("数据库更新失败，没有返回数据")
                            
                    except Exception as e:
                        print(f"更新数据库时发生错误: {str(e)}")
                        print(f"错误详情: {type(e).__name__}")
                        import traceback
                        print(f"错误堆栈: {traceback.format_exc()}")
                
                    print(f"成功更新 {symbol} 的价格: {current_price}")
                else:
                    print(f"获取 {symbol} 价格失败")
            else:
                print(f"\n跳过已平仓的股票: {trade['symbol']}")
                
    except Exception as e:
        print(f"更新股票价格时发生错误: {str(e)}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")

# 创建调度器
scheduler = BackgroundScheduler()
scheduler.start()

# 添加定时任务，每30秒更新一次价格
scheduler.add_job(
    func=update_holding_stocks_prices,
    trigger=IntervalTrigger(seconds=30),  # 改为30秒
    id='update_stock_prices',
    name='Update holding stocks prices every 30 seconds',
    replace_existing=True
)

print("价格更新定时任务已启动，每30秒更新一次")

@app.route('/api/check-login', methods=['GET'])
def check_login():
    try:
        if 'user_id' in session:
            # 获取用户信息
            response = supabase.table('users').select('*').eq('id', session['user_id']).execute()
            if response.data:
                user = response.data[0]
                return jsonify({
                    'isLoggedIn': True,
                    'user': {
                        'id': user['id'],
                        'username': user['username'],
                        'role': user.get('role', 'user'),
                        'email': user.get('email'),
                        'avatar_url': user.get('avatar_url')
                    }
                })
        
        return jsonify({'isLoggedIn': False})
    except Exception as e:
        print(f"Check login error: {str(e)}")
        return jsonify({'isLoggedIn': False}), 500

# --- 管理员接口 ---
@app.route('/api/admin/users', methods=['GET', 'POST'])
def manage_users():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        if request.method == 'GET':
            # 获取所有用户
            response = supabase.table('users').select('*').execute()
            
            # 过滤敏感信息
            users = []
            for user in response.data:
                users.append({
                    'id': user['id'],
                    'username': user['username'],
                    'email': user.get('email'),
                    'role': user.get('role', 'user'),
                    'status': user.get('status', 'active'),
                    'membership_level': user.get('membership_level', '普通会员'),
                    'last_login': user.get('last_login'),
                    'last_login_ip': user.get('last_login_ip'),
                    'last_login_location': user.get('last_login_location'),
                    'created_at': user.get('created_at')
                })
                
            return jsonify({
                'success': True,
                'users': users
            })
            
        elif request.method == 'POST':
            # 创建新用户
            data = request.get_json()
            
            # 检查必要字段
            if not data.get('username') or not data.get('password'):
                return jsonify({'success': False, 'message': '用户名和密码是必填项'}), 400
                
            # 检查用户名是否已存在
            check_response = supabase.table('users').select('id').eq('username', data['username']).execute()
            if check_response.data:
                return jsonify({'success': False, 'message': '用户名已存在'}), 400
                
            # 创建新用户
            new_user = {
                'username': data['username'],
                'password_hash': data['password'],  # 在实际应用中应该对密码进行加密
                'email': data.get('email'),
                'role': data.get('role', 'user'),
                'status': 'active',
                'membership_level': '普通会员',
                'created_at': datetime.now(pytz.UTC).isoformat()
            }
            
            response = supabase.table('users').insert(new_user).execute()
            
            return jsonify({
                'success': True,
                'message': '用户创建成功',
                'user_id': response.data[0]['id']
            })
            
    except Exception as e:
        print(f"Manage users error: {str(e)}")
        return jsonify({'success': False, 'message': '操作失败'}), 500

@app.route('/api/admin/users/<user_id>', methods=['PUT', 'DELETE'])
def update_user(user_id):
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        if request.method == 'PUT':
            data = request.get_json()
            
            # 只允许更新特定字段
            allowed_fields = ['status', 'role', 'password_hash']
            update_data = {k: v for k, v in data.items() if k in allowed_fields}
            
            if not update_data:
                return jsonify({'success': False, 'message': '没有可更新的字段'}), 400
                
            # 更新用户信息
            response = supabase.table('users').update(update_data).eq('id', user_id).execute()
            
            if not response.data:
                return jsonify({'success': False, 'message': '用户不存在'}), 404
                
            return jsonify({
                'success': True,
                'message': '更新成功'
            })
            
        elif request.method == 'DELETE':
            # 软删除用户（更新状态为inactive）
            response = supabase.table('users').update({
                'status': 'inactive',
                'deleted_at': datetime.now(pytz.UTC).isoformat()
            }).eq('id', user_id).execute()
            
            if not response.data:
                return jsonify({'success': False, 'message': '用户不存在'}), 404
                
            return jsonify({
                'success': True,
                'message': '用户已禁用'
            })
            
    except Exception as e:
        print(f"Update user error: {str(e)}")
        return jsonify({'success': False, 'message': '操作失败'}), 500

@app.route('/api/admin/users/batch', methods=['POST'])
def batch_update_users():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        action = data.get('action')  # 'activate' 或 'deactivate'
        
        if not user_ids or action not in ['activate', 'deactivate']:
            return jsonify({'success': False, 'message': '参数错误'}), 400
            
        # 批量更新用户状态
        status = 'active' if action == 'activate' else 'inactive'
        response = supabase.table('users').update({
            'status': status
        }).in_('id', user_ids).execute()
        
        return jsonify({
            'success': True,
            'message': f'已{action} {len(response.data)} 个用户'
        })
        
    except Exception as e:
        print(f"Batch update error: {str(e)}")
        return jsonify({'success': False, 'message': '批量操作失败'}), 500

@app.route('/api/admin/logs', methods=['GET'])
def get_login_logs():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        # 获取最近100条登录记录
        response = supabase.table('users').select('username, last_login, status').order('last_login', desc=True).limit(100).execute()
        
        return jsonify({
            'success': True,
            'logs': response.data
        })
        
    except Exception as e:
        print(f"Get logs error: {str(e)}")
        return jsonify({'success': False, 'message': '获取日志失败'}), 500

# --- 测试路由 ---
@app.route('/test/login', methods=['GET'])
def test_login():
    test_cases = [
        {
            'name': '正常登录',
            'data': {'username': 'admin', 'password': '123456'},
            'expected': {'success': True, 'message': '登录成功'}
        },
        {
            'name': '缺少用户名',
            'data': {'password': '123456'},
            'expected': {'success': False, 'message': '请输入账号和密码'}
        },
        {
            'name': '缺少密码',
            'data': {'username': 'admin'},
            'expected': {'success': False, 'message': '请输入账号和密码'}
        },
        {
            'name': '错误密码',
            'data': {'username': 'admin', 'password': 'wrong_password'},
            'expected': {'success': False, 'message': '密码错误'}
        },
        {
            'name': '不存在的用户',
            'data': {'username': 'non_existent_user', 'password': '123456'},
            'expected': {'success': False, 'message': '账号不存在'}
        }
    ]
    
    results = []
    for test in test_cases:
        try:
            # 创建测试请求
            with app.test_request_context('/api/login', method='POST', json=test['data']):
                # 调用登录函数
                response = login()
                # 如果response是元组，取第一个元素（JSON响应）
                if isinstance(response, tuple):
                    data = response[0].get_json()
                else:
                    data = response.get_json()
                
                # 检查结果
                passed = (
                    data['success'] == test['expected']['success'] and
                    data['message'] == test['expected']['message']
                )
                
                results.append({
                    'test_case': test['name'],
                    'passed': passed,
                    'expected': test['expected'],
                    'actual': data
                })
        except Exception as e:
            results.append({
                'test_case': test['name'],
                'passed': False,
                'error': str(e),
                'expected': test['expected'],
                'actual': '测试执行出错'
            })
    
    return render_template('test_results.html', results=results)

# --- 管理后台路由 ---
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('vip'))
        
    if session.get('role') != 'admin':
        return redirect(url_for('vip'))
    
    return render_template('admin/dashboard.html', admin_name=session.get('username', 'Admin'))

# --- 交易策略管理路由 ---
@app.route('/admin/strategy')
def admin_strategy():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('vip'))
    return render_template('admin/strategy.html', admin_name=session.get('username', 'Admin'))

# --- 策略管理API ---
@app.route('/api/admin/strategy', methods=['GET', 'POST', 'DELETE'])
def manage_strategy():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        if request.method == 'GET':
            # 获取最新的交易策略
            strategy_response = supabase.table('trading_strategies').select("*").order('updated_at', desc=True).limit(1).execute()
            
            if strategy_response.data:
                strategy = strategy_response.data[0]
                # 确保 trading_focus 是列表格式
                trading_focus = strategy['trading_focus']
                if isinstance(trading_focus, str):
                    try:
                        trading_focus = json.loads(trading_focus)
                    except:
                        trading_focus = [trading_focus]
                        
                return jsonify({
                    'success': True,
                    'strategy': {
                        'id': strategy['id'],
                        'market_analysis': strategy['market_analysis'],
                        'trading_focus': trading_focus,
                        'risk_warning': strategy['risk_warning'],
                        'updated_at': strategy['updated_at']
                    }
                })
            return jsonify({'success': True, 'strategy': None})
            
        elif request.method == 'POST':
            # 创建新策略
            data = request.get_json()
            required_fields = ['market_analysis', 'trading_focus', 'risk_warning']
            
            if not all(field in data for field in required_fields):
                return jsonify({'success': False, 'message': '缺少必要字段'}), 400
                
            # 确保 trading_focus 是列表格式
            trading_focus = data['trading_focus']
            if isinstance(trading_focus, str):
                try:
                    trading_focus = json.loads(trading_focus)
                except:
                    trading_focus = [trading_focus]
                    
            # 插入新策略
            strategy_data = {
                'market_analysis': data['market_analysis'],
                'trading_focus': trading_focus,
                'risk_warning': data['risk_warning'],
                'updated_at': datetime.now(pytz.UTC).isoformat()
            }
            
            try:
                response = supabase.table('trading_strategies').insert(strategy_data).execute()
                
                if not response.data:
                    return jsonify({'success': False, 'message': '创建失败'}), 500
                    
                return jsonify({'success': True, 'message': '策略保存成功'})
            except Exception as e:
                print(f"Error creating strategy: {str(e)}")
                return jsonify({'success': False, 'message': f'创建失败: {str(e)}'}), 500
            
        elif request.method == 'DELETE':
            strategy_id = request.args.get('id')
            if not strategy_id:
                return jsonify({'success': False, 'message': '缺少策略ID'}), 400
                
            response = supabase.table('trading_strategies').delete().eq('id', strategy_id).execute()
            
            if not response.data:
                return jsonify({'success': False, 'message': '删除失败'}), 500
                
            return jsonify({'success': True, 'message': '策略删除成功'})
            
    except Exception as e:
        print(f"Strategy management error: {str(e)}")
        return jsonify({'success': False, 'message': '操作失败'}), 500

@app.route('/api/admin/strategy/history', methods=['GET'])
def get_strategy_history():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        # 从 Supabase 获取所有策略记录，按时间倒序排列
        response = supabase.table('trading_strategies').select("*").order('updated_at', desc=True).execute()
        
        if not response.data:
            return jsonify({
                'success': True,
                'history': []
            })
        
        history = []
        for record in response.data:
            # 确保 trading_focus 是列表格式
            trading_focus = record['trading_focus']
            if isinstance(trading_focus, str):
                try:
                    trading_focus = json.loads(trading_focus)
                except:
                    trading_focus = [trading_focus]
                    
            history.append({
                'id': record['id'],
                'market_analysis': record['market_analysis'],
                'trading_focus': trading_focus,
                'risk_warning': record['risk_warning'],
                'modified_at': record['updated_at'],
                'modified_by': 'admin'  # 暂时固定为admin
            })
            
        return jsonify({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        print(f"Get strategy history error: {str(e)}")
        return jsonify({'success': False, 'message': '获取历史记录失败'}), 500

@app.route('/admin/strategy/permissions')
def strategy_permissions():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    return render_template('admin/strategy_permissions.html', admin_name=session.get('username', 'Admin'))

# --- 删除策略历史记录 ---
@app.route('/api/admin/strategy/history/<int:history_id>', methods=['DELETE'])
def delete_strategy_history(history_id):
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        # 从 Supabase 删除历史记录
        response = supabase.table('strategy_history').delete().eq('id', history_id).execute()
        
        if not response.data:
            return jsonify({'success': False, 'message': '删除失败，记录不存在'}), 404
            
        return jsonify({'success': True, 'message': '历史记录删除成功'})
        
    except Exception as e:
        print(f"Delete strategy history error: {str(e)}")
        return jsonify({'success': False, 'message': '删除失败'}), 500

# --- 股票交易管理路由 ---
@app.route('/admin/trading')
def admin_trading():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('vip'))
    return render_template('admin/trading.html', admin_name=session.get('username', 'Admin'))

# --- 股票交易管理API ---
@app.route('/api/admin/trading', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_trading():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        if request.method == 'GET':
            # 获取所有交易记录
            response = supabase.table('trades1').select("*").order('entry_date', desc=True).execute()
            
            trades = []
            for trade in response.data:
                trades.append({
                    'id': trade['id'],
                    'symbol': trade['symbol'],
                    'entry_price': trade['entry_price'],
                    'exit_price': trade.get('exit_price'),
                    'size': trade['size'],
                    'entry_date': trade['entry_date'],
                    'exit_date': trade.get('exit_date'),
                    'status': 'Closed' if trade.get('exit_price') else 'Active',
                    'profit_amount': (trade.get('exit_price', 0) - trade['entry_price']) * trade['size'] if trade.get('exit_price') else 0
                })
                
            return jsonify({
                'success': True,
                'trades': trades
            })
            
        elif request.method == 'POST':
            # 创建新交易记录
            data = request.get_json()
            required_fields = ['symbol', 'entry_price', 'size']
            
            if not all(field in data for field in required_fields):
                return jsonify({'success': False, 'message': '缺少必要字段'}), 400
                
            trade_data = {
                'symbol': data['symbol'],
                'entry_price': data['entry_price'],
                'size': data['size'],
                'entry_date': data.get('entry_date') or datetime.now(pytz.UTC).isoformat(),
                'current_price': data['entry_price']
            }
            
            response = supabase.table('trades1').insert(trade_data).execute()
            
            return jsonify({
                'success': True,
                'message': '交易记录创建成功'
            })
            
        elif request.method == 'PUT':
            # 更新交易记录
            data = request.get_json()
            trade_id = data.get('id')
            
            if not trade_id:
                return jsonify({'success': False, 'message': '缺少交易ID'}), 400
                
            update_data = {}
            if 'exit_price' in data:
                update_data['exit_price'] = data['exit_price']
                # 使用用户提供的 exit_date，如果没有提供则使用当前时间
                if 'exit_date' in data and data['exit_date']:
                    # 将本地时间转换为 UTC 时间
                    local_date = datetime.fromisoformat(data['exit_date'].replace('Z', '+00:00'))
                    update_data['exit_date'] = local_date.astimezone(pytz.UTC).isoformat()
                else:
                    update_data['exit_date'] = datetime.now(pytz.UTC).isoformat()
                
            if update_data:
                response = supabase.table('trades1').update(update_data).eq('id', trade_id).execute()
                
            return jsonify({
                'success': True,
                'message': '交易记录更新成功'
            })
            
        elif request.method == 'DELETE':
            trade_id = request.args.get('id')
            if not trade_id:
                return jsonify({'success': False, 'message': '缺少交易ID'}), 400
                
            response = supabase.table('trades1').delete().eq('id', trade_id).execute()
            
            return jsonify({
                'success': True,
                'message': '交易记录删除成功'
            })
            
    except Exception as e:
        print(f"Trading management error: {str(e)}")
        return jsonify({'success': False, 'message': '操作失败'}), 500

# --- 排行榜管理路由 ---
@app.route('/admin/leaderboard')
def admin_leaderboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('vip'))
    return render_template('admin/leaderboard.html', admin_name=session.get('username', 'Admin'))

# --- 排行榜管理API ---
@app.route('/api/admin/leaderboard', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_leaderboard():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        if request.method == 'GET':
            # 获取排行榜数据
            response = supabase.table('leaderboard_traders').select("*").order('total_profit', desc=True).execute()
            
            return jsonify({
                'success': True,
                'leaderboard': response.data
            })
            
        elif request.method == 'POST':
            # 添加新的排行榜记录
            data = request.get_json()
            required_fields = ['trader_name', 'total_profit', 'win_rate', 'total_trades', 'profile_image_url']
            
            if not all(field in data for field in required_fields):
                return jsonify({'success': False, 'message': '缺少必要字段'}), 400
                
            leaderboard_data = {
                'trader_name': data['trader_name'],
                'total_profit': data['total_profit'],
                'win_rate': data['win_rate'],
                'total_trades': data['total_trades'],
                'profile_image_url': data['profile_image_url'],
                'updated_at': datetime.now(pytz.UTC).isoformat()
            }
            
            response = supabase.table('leaderboard_traders').insert(leaderboard_data).execute()
            
            return jsonify({
                'success': True,
                'message': '排行榜记录添加成功'
            })
            
        elif request.method == 'PUT':
            # 更新排行榜记录
            data = request.get_json()
            record_id = data.get('id')
            
            if not record_id:
                return jsonify({'success': False, 'message': '缺少记录ID'}), 400
                
            update_data = {
                'trader_name': data.get('trader_name'),
                'total_profit': data.get('total_profit'),
                'win_rate': data.get('win_rate'),
                'total_trades': data.get('total_trades'),
                'profile_image_url': data.get('profile_image_url'),
                'updated_at': datetime.now(pytz.UTC).isoformat()
            }
            
            response = supabase.table('leaderboard_traders').update(update_data).eq('id', record_id).execute()
            
            return jsonify({
                'success': True,
                'message': '排行榜记录更新成功'
            })
            
        elif request.method == 'DELETE':
            record_id = request.args.get('id')
            if not record_id:
                return jsonify({'success': False, 'message': '缺少记录ID'}), 400
                
            response = supabase.table('leaderboard_traders').delete().eq('id', record_id).execute()
            
            return jsonify({
                'success': True,
                'message': '排行榜记录删除成功'
            })
            
    except Exception as e:
        print(f"Leaderboard management error: {str(e)}")
        return jsonify({'success': False, 'message': '操作失败'}), 500

# --- 交易记录表自动建表 ---
def init_trading_db():
    try:
        # 创建交易记录表
        response = supabase.table('trades1').select("*").limit(1).execute()
    except:
        # 如果表不存在，创建表
        supabase.table('trades1').create({
            'id': 'uuid',
            'symbol': 'text',
            'entry_price': 'numeric',
            'exit_price': 'numeric',
            'size': 'numeric',
            'entry_date': 'timestamp with time zone',
            'exit_date': 'timestamp with time zone',
            'current_price': 'numeric',
            'user_id': 'uuid',
            'created_at': 'timestamp with time zone',
            'updated_at': 'timestamp with time zone'
        })

# --- 排行榜表自动建表 ---
def init_leaderboard_db():
    try:
        # 创建排行榜表
        response = supabase.table('leaderboard').select("*").limit(1).execute()
    except:
        # 如果表不存在，创建表
        supabase.table('leaderboard').create({
            'id': 'uuid',
            'user_id': 'uuid',
            'profit': 'numeric',
            'win_rate': 'numeric',
            'total_trades': 'integer',
            'winning_trades': 'integer',
            'losing_trades': 'integer',
            'created_at': 'timestamp with time zone',
            'updated_at': 'timestamp with time zone'
        })

# --- 添加测试数据 ---
def add_test_data():
    try:
        # 添加测试交易记录
        trades_data = [
            {
                'symbol': 'AAPL',
                'entry_price': 150.25,
                'size': 100,
                'entry_date': datetime.now(pytz.UTC).isoformat(),
                'current_price': 155.30,
                'created_at': datetime.now(pytz.UTC).isoformat(),
                'updated_at': datetime.now(pytz.UTC).isoformat()
            },
            {
                'symbol': 'GOOGL',
                'entry_price': 2750.00,
                'exit_price': 2800.00,
                'size': 10,
                'entry_date': datetime.now(pytz.UTC).isoformat(),
                'exit_date': datetime.now(pytz.UTC).isoformat(),
                'current_price': 2800.00,
                'created_at': datetime.now(pytz.UTC).isoformat(),
                'updated_at': datetime.now(pytz.UTC).isoformat()
            }
        ]
        
        # 检查是否已有交易记录
        response = supabase.table('trades1').select("*").execute()
        if not response.data:
            for trade in trades_data:
                supabase.table('trades1').insert(trade).execute()
                
        # 添加测试排行榜数据
        leaderboard_data = [
            {
                'user_id': '1',
                'profit': 15000.00,
                'win_rate': 85.5,
                'total_trades': 100,
                'winning_trades': 85,
                'losing_trades': 15,
                'created_at': datetime.now(pytz.UTC).isoformat(),
                'updated_at': datetime.now(pytz.UTC).isoformat()
            },
            {
                'user_id': '2',
                'profit': 8500.00,
                'win_rate': 75.0,
                'total_trades': 80,
                'winning_trades': 60,
                'losing_trades': 20,
                'created_at': datetime.now(pytz.UTC).isoformat(),
                'updated_at': datetime.now(pytz.UTC).isoformat()
            }
        ]
        
        # 检查是否已有排行榜数据
        response = supabase.table('leaderboard').select("*").execute()
        if not response.data:
            for record in leaderboard_data:
                supabase.table('leaderboard').insert(record).execute()
                
    except Exception as e:
        print(f"Error adding test data: {str(e)}")

@app.route('/api/trader/<trader_name>')
def get_trader_data(trader_name):
    try:
        # Get trader data from Supabase
        response = supabase.table('leaderboard_traders')\
            .select('*')\
            .eq('trader_name', trader_name)\
            .single()\
            .execute()
            
        if response.data:
            return jsonify({
                'success': True,
                'trader': response.data
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Trader not found'
            }), 404
            
    except Exception as e:
        print(f"Error fetching trader data: {e}")
        return jsonify({
            'success': False,
            'message': 'Error fetching trader data'
        }), 500

@app.route('/api/like-trader/<trader_name>', methods=['POST'])
def like_trader(trader_name):
    try:
        # Get trader data from Supabase
        response = supabase.table('leaderboard_traders')\
            .select('*')\
            .eq('trader_name', trader_name)\
            .single()\
            .execute()
            
        if response.data:
            # Update likes count
            current_likes = response.data.get('likes_count', 0)
            updated_likes = current_likes + 1
            
            # Update in database
            supabase.table('leaderboard_traders')\
                .update({'likes_count': updated_likes})\
                .eq('trader_name', trader_name)\
                .execute()
                
            return jsonify({
                'success': True,
                'likes_count': updated_likes
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Trader not found'
            }), 404
            
    except Exception as e:
        print(f"Error updating likes: {e}")
        return jsonify({
            'success': False,
            'message': 'Error updating likes'
        }), 500

@app.route('/api/admin/trade/upload-image', methods=['POST'])
def upload_trade_image():
    try:
        print('supabase type:', type(supabase))
        trade_id = request.form.get('trade_id')
        file = request.files.get('image')
        if not trade_id or not file:
            return jsonify({'success': False, 'message': 'Missing trade_id or image'}), 400
        # 生成唯一文件名
        ext = os.path.splitext(secure_filename(file.filename))[1] or '.jpg'
        unique_name = f"avatars/trade_{trade_id}_{uuid.uuid4().hex}{ext}"
        # 上传到Supabase Storage
        file_bytes = file.read()
        # 修正调用方式，兼容本地 supabase-py 版本
        result = supabase.storage.from_('avatars').upload(
            unique_name,
            file_bytes,
            file_options={"content-type": file.content_type}
        )
        # 获取图片URL
        file_url = supabase.storage.from_('avatars').get_public_url(unique_name)
        # 更新trades1表
        supabase.table('trades1').update({'image_url': file_url}).eq('id', trade_id).execute()
        return jsonify({'success': True, 'url': file_url})
    except Exception as e:
        print(f"Trade image upload error: {str(e)}")
        return jsonify({'success': False, 'message': 'Upload failed'}), 500

@app.route('/api/admin/whatsapp-agents', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_whatsapp_agents():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        if request.method == 'GET':
            # 获取所有WhatsApp客服
            response = supabase.table('whatsapp_agents').select("*").execute()
            return jsonify({
                'success': True,
                'agents': response.data
            })
            
        elif request.method == 'POST':
            # 添加新的WhatsApp客服
            data = request.get_json()
            required_fields = ['name', 'phone_number']
            
            if not all(field in data for field in required_fields):
                return jsonify({'success': False, 'message': '缺少必要字段'}), 400
                
            # 验证电话号码格式
            phone_number = data['phone_number']
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number
                
            agent_data = {
                'name': data['name'],
                'phone_number': phone_number,
                'is_active': data.get('is_active', True),
                'created_at': datetime.now(pytz.UTC).isoformat(),
                'updated_at': datetime.now(pytz.UTC).isoformat()
            }
            
            response = supabase.table('whatsapp_agents').insert(agent_data).execute()
            
            return jsonify({
                'success': True,
                'message': 'WhatsApp客服添加成功',
                'agent': response.data[0] if response.data else None
            })
            
        elif request.method == 'PUT':
            # 更新WhatsApp客服信息
            data = request.get_json()
            agent_id = data.get('id')
            
            if not agent_id:
                return jsonify({'success': False, 'message': '缺少客服ID'}), 400
                
            update_data = {}
            if 'name' in data:
                update_data['name'] = data['name']
            if 'phone_number' in data:
                phone_number = data['phone_number']
                if not phone_number.startswith('+'):
                    phone_number = '+' + phone_number
                update_data['phone_number'] = phone_number
            if 'is_active' in data:
                update_data['is_active'] = data['is_active']
                
            update_data['updated_at'] = datetime.now(pytz.UTC).isoformat()
            
            response = supabase.table('whatsapp_agents').update(update_data).eq('id', agent_id).execute()
            
            return jsonify({
                'success': True,
                'message': 'WhatsApp客服更新成功',
                'agent': response.data[0] if response.data else None
            })
            
        elif request.method == 'DELETE':
            # 删除WhatsApp客服
            agent_id = request.args.get('id')
            if not agent_id:
                return jsonify({'success': False, 'message': '缺少客服ID'}), 400
                
            response = supabase.table('whatsapp_agents').delete().eq('id', agent_id).execute()
            
            return jsonify({
                'success': True,
                'message': 'WhatsApp客服删除成功'
            })
            
    except Exception as e:
        print(f"Manage WhatsApp agents error: {str(e)}")
        return jsonify({'success': False, 'message': '操作失败'}), 500

if __name__ == '__main__':
    # 初始化数据库
    init_user_db()
    init_membership_levels_db()
    init_user_membership_db()
    
    # 启动应用
    app.run(debug=True)
