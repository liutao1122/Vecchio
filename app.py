from flask import Flask, render_template, request, jsonify, redirect, url_for, session
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
from supabase_client import get_traders  # Import the get_traders function
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_secret_key_here')  # 使用环境变量

# Supabase配置
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
if not url or not key:
    raise ValueError("Missing required environment variables: SUPABASE_URL and SUPABASE_KEY")
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

def format_datetime(dt_str):
    """将UTC时间字符串转换为本地时间并格式化"""
    try:
        # 解析UTC时间字符串
        dt = datetime.strptime(dt_str.split('+')[0], '%Y-%m-%d %H:%M:%S.%f')
        # 设置为UTC时区
        dt = pytz.UTC.localize(dt)
        # 转换为中国时区
        china_tz = pytz.timezone('Asia/Shanghai')
        dt = dt.astimezone(china_tz)
        # 格式化为易读格式
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return dt_str

def get_real_time_price(symbol):
    """获取实时股票价格"""
    try:
        api_key = "g_M1OstKnY6engOcJarC_JN1TkWZqL6w"
        url = f"https://api.stockdata.org/v1/data/quote?symbols={symbol}&api_token={api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['data'] and len(data['data']) > 0:
                return float(data['data'][0]['price'])
        return None
    except Exception as e:
        print(f"Error getting price for {symbol}: {str(e)}")
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
        response = supabase.table('trades').select("*").execute()
        trades = response.data
        
        if not trades:
            print("No trades found in database")
            trades = []
        
        # 为每个交易添加图片URL
        for trade in trades:
            # 优先使用数据库中的 image_url，否则用 STOCK_IMAGES
            trade['image_url'] = trade.get('image_url') or STOCK_IMAGES.get(trade['symbol'], '')
            
            # 如果没有current_price，获取实时价格
            if 'current_price' not in trade or not trade['current_price']:
                current_price = get_real_time_price(trade['symbol'])
                if current_price:
                    trade['current_price'] = current_price
                    trade['current_amount'] = current_price * trade['size']
                    trade['profit_amount'] = trade['current_amount'] - trade['entry_amount']
                    trade['profit_ratio'] = (trade['profit_amount'] / trade['entry_amount']) * 100
        
        # 计算总览数据
        total_trades = len(trades)
        
        # 获取当前持仓
        positions = [t for t in trades if t['status'] in ['Active', '持有中']]
        
        # 计算当月平仓盈亏
        current_month = datetime.now().strftime('%Y-%m')
        monthly_closed_trades = [t for t in trades 
                               if t['status'] in ['Take Profit', 'Stop Loss', '以止盈', '以止损'] 
                               and 'exit_date' in t 
                               and t['exit_date'] 
                               and t['exit_date'].startswith(current_month)]
        
        # 添加调试信息
        print("=== Monthly Profit Debug ===")
        print(f"Current Month: {current_month}")
        print(f"Monthly Closed Trades Count: {len(monthly_closed_trades)}")
        print("Monthly Closed Trades:")
        for trade in monthly_closed_trades:
            print(f"Trade: {trade.get('symbol')} - Status: {trade.get('status')} - Profit: {trade.get('profit_amount')}")
        
        monthly_profit = sum(t.get('profit_amount', 0) for t in monthly_closed_trades)
        print(f"Total Monthly Profit: {monthly_profit}")
        
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
            'updated_at': datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S.%f+00')
        }
        
        # 格式化更新时间
        if strategy_info.get('updated_at'):
            strategy_info['formatted_time'] = format_datetime(strategy_info['updated_at'])
        
        # 设置个人信息
        trader_info = {
            'trader_name': 'Professional Trader',
            'professional_title': 'Financial Trading Expert | Technical Analysis Master',
            'bio': 'Focused on US stock market technical analysis and quantitative trading',
            'positions': positions,
            'monthly_profit': round(monthly_profit, 2),
            'active_trades': len(positions),
            'total_profit': round(3000000 + sum(t.get('profit_amount', 0) for t in trades), 2),
            'strategy_info': strategy_info
        }

        # 从数据库获取头像URL
        profile_response = supabase.table('trader_profiles').select('profile_image_url').limit(1).execute()
        if profile_response.data:
            trader_info['profile_image_url'] = profile_response.data[0].get('profile_image_url')

        # 添加调试日志
        print("=== Debug Info ===")
        print(f"Profile Image URL: {trader_info.get('profile_image_url')}")
        print("=== Trader Info ===")
        print(trader_info)
        
        return render_template('index.html', 
                            trades=trades,
                            trader_info=trader_info)
    except Exception as e:
        print(f"Error in index route: {e}")
        return render_template('index.html', 
                            trades=[],
                            trader_info={
                                'trader_name': 'System Error', 
                                'monthly_profit': 0, 
                                'active_trades': 0
                            })

@app.route('/api/trader-profile', methods=['GET'])
def trader_profile():
    try:
        # 获取个人资料
        response = supabase.table('trader_profiles').select('*').limit(1).execute()
        
        # 获取trades表中的记录数
        trades_response = supabase.table('trades').select('id').execute()
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
    traders = get_traders(sort_by)
    
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
        result = supabase.storage.from_('avatars').upload(
            unique_filename,
            file_bytes,
            file_options={"content-type": file.content_type}
        )

        # 获取文件URL
        file_url = supabase.storage.from_('avatars').get_public_url(unique_filename)

        # 获取第一个交易员的ID（因为目前是单用户系统）
        profile_response = supabase.table('trader_profiles').select('id').limit(1).execute()
        if not profile_response.data:
            # 如果没有找到交易员记录，创建一个新记录
            trader_data = {
                'trader_name': 'Professional Trader',
                'professional_title': 'Financial Trading Expert',
                'created_at': datetime.now(pytz.UTC).isoformat(),
                'updated_at': datetime.now(pytz.UTC).isoformat()
            }
            profile_response = supabase.table('trader_profiles').insert(trader_data).execute()
        
        trader_id = profile_response.data[0]['id']

        # 将之前的头像标记为非当前
        supabase.table('avatar_history').update({
            'is_current': False
        }).eq('user_id', trader_id).execute()

        # 插入新的头像记录
        avatar_data = {
            'user_id': trader_id,
            'image_url': file_url,
            'storage_path': unique_filename,
            'file_name': file.filename,
            'file_size': file_size,
            'mime_type': file.content_type,
            'is_current': True
        }
        supabase.table('avatar_history').insert(avatar_data).execute()

        # 更新用户个人资料
        supabase.table('trader_profiles').update({
            'profile_image_url': file_url,
            'updated_at': datetime.now(pytz.UTC).isoformat()
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
        # 已登录，从Supabase users表查找当前用户信息
        username = session['username']
        response = supabase.table('users').select('*').eq('username', username).execute()
        user = response.data[0] if response.data else None
        trader_info = {
            'trader_name': user['username'],
            'profile_image_url': user.get('profile_image_url', 'https://via.placeholder.com/180'),
            'professional_title': user.get('professional_title', 'VIP会员'),
            # 你可以根据users表结构补充更多字段
        } if user else None
        return render_template('vip.html', trader_info=trader_info)
    else:
        # 未登录，不传trader_info，只渲染登录入口
        return render_template('vip.html')

# --- 用户表自动建表 ---
def init_user_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_user_db()

# --- 登录接口（Supabase版） ---
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or request.form
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'success': False, 'message': '请输入账号和密码'}), 400
    # 用Supabase校验账号密码（查password_hash字段）
    response = supabase.table('users').select('*').eq('username', username).eq('password_hash', password).execute()
    print('Login debug:', username, password)  # 新增调试输出
    print('Supabase response:', response.data)  # 新增调试输出
    user = response.data[0] if response.data else None
    if user:
        session['user_id'] = user.get('id') or user.get('uuid')
        session['username'] = username
        return jsonify({'success': True, 'message': '登录成功'})
    else:
        return jsonify({'success': False, 'message': '账号或密码错误'}), 401

# --- 登出接口 ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('vip'))

if __name__ == '__main__':
    app.run(debug=True) 
