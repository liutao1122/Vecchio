import yfinance as yf
import requests

def get_apple_price():
    try:
        # 方法1：使用 yfinance
        apple = yf.Ticker("AAPL")
        price = apple.info.get('currentPrice')
        if price:
            print(f"通过 yfinance 获取的苹果股价: ${price}")
            return
        
        # 方法2：使用 Alpha Vantage
        api_keys = [
            '5DMGYRZFN6H41J8D',
            '09H83INPNIZNDVH9',
            'GWDRK755PQ71W2KY',
            'T19PAWDXV2H4S6H7',
            'BQA3W5X7N3FTQ99N',
            '1RD089JXRRYFT2PX',
            'ODM4KNP3OFW736UT'
        ]
        
        for api_key in api_keys:
            url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey={api_key}'
            response = requests.get(url)
            data = response.json()
            if 'Global Quote' in data and '05. price' in data['Global Quote']:
                price = float(data['Global Quote']['05. price'])
                print(f"通过 Alpha Vantage 获取的苹果股价: ${price}")
                return
        
        print("无法获取苹果股价，所有方法都失败了")
        
    except Exception as e:
        print(f"获取股价时发生错误: {str(e)}")

if __name__ == "__main__":
    get_apple_price() 