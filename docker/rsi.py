import requests
import pandas as pd
import ta
import time

# 你的钉钉机器人 Webhook 地址
DINGTALK_WEBHOOK = 'https://oapi.dingtalk.com/robot/send?access_token=2b0290fb302585f36c81928cf9a16dd343cbafd5232392a33f7de8da81c71cdb'

def send_ding_alert(content):
    data = {
        "msgtype": "text",
        "text": {"content": content}
    }
    headers = {'Content-Type': 'application/json'}
    try:
        res = requests.post(DINGTALK_WEBHOOK, headers=headers, json=data, timeout=10)
        if res.status_code == 200:
            print("✅ 钉钉提醒发送成功")
        else:
            print("⚠️ 钉钉提醒失败：", res.text)
    except Exception as e:
        print("❌ 钉钉发送异常：", e)

def get_okx_klines(inst_id="BTC-USDT", bar="5m", limit=100):
    url = "https://www.okx.com/api/v5/market/candles"
    params = {
        "instId": inst_id,
        "bar": bar,
        "limit": limit
    }
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != "0":
            print(f"❌ OKX接口错误: {data.get('msg')}")
            return None
        kline = data["data"]
    except Exception as e:
        print(f"❌ 获取OKX行情失败：{e}")
        return None

    df = pd.DataFrame(kline, columns=[
        "ts", "open", "high", "low", "close", "volume", "volCcy", "tradeNum", "buyVolume"
    ])
    df["close"] = pd.to_numeric(df["close"], errors='coerce')
    df["ts"] = pd.to_datetime(df["ts"].astype(int), unit='ms')
    df.sort_values(by="ts", inplace=True)
    return df

def calculate_rsi(df, period=14):
    if df is None or len(df) < period + 1:
        print("⚠️ 数据不足，无法计算 RSI")
        return None
    df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=period).rsi()
    return df

# 全局状态变量，保存是否处于超买和超卖状态
last_rsi_overbought = None
last_rsi_oversold = None

def check_rsi(df):
    global last_rsi_overbought, last_rsi_oversold

    if df is None or 'rsi' not in df.columns or df['rsi'].dropna().empty:
        print("⚠️ RSI数据不足，无法计算")
        return

    latest_rsi = df['rsi'].dropna().iloc[-1]
    latest_price = df['close'].iloc[-1]

    print(f"当前 5分钟 RSI：{latest_rsi:.2f}，价格：{latest_price:.2f}")

    # 超买逻辑
    if last_rsi_overbought is None:
        last_rsi_overbought = latest_rsi > 70
    else:
        if not last_rsi_overbought and latest_rsi > 70:
            print("⚠️ RSI 上穿70，超买警告")
            send_ding_alert(f"⚠️ RSI 上穿70！RSI达到{latest_rsi:.2f}，价格：{latest_price:.2f}，可能是卖出信号。")
            last_rsi_overbought = True
        elif last_rsi_overbought and latest_rsi <= 70:
            print("ℹ️ RSI 下降回70以下")
            send_ding_alert(f"ℹ️ RSI 下降回70以下，当前RSI {latest_rsi:.2f}，价格：{latest_price:.2f}。")
            last_rsi_overbought = False

    # 超卖逻辑
    if last_rsi_oversold is None:
        last_rsi_oversold = latest_rsi < 30
    else:
        if not last_rsi_oversold and latest_rsi < 30:
            print("⚠️ RSI 下穿30，超卖警告")
            send_ding_alert(f"⚠️ RSI 下穿30！RSI达到{latest_rsi:.2f}，价格：{latest_price:.2f}，可能是买入信号。")
            last_rsi_oversold = True
        elif last_rsi_oversold and latest_rsi >= 30:
            print("ℹ️ RSI 上升回30以上")
            send_ding_alert(f"ℹ️ RSI 上升回30以上，当前RSI {latest_rsi:.2f}，价格：{latest_price:.2f}。")
            last_rsi_oversold = False

    # 正常区间提示
    if 30 <= latest_rsi <= 70:
        print("RSI 处于正常区间，无需报警")

def main():
    send_ding_alert("✅ RSI监控脚本已启动，开始实时监控市场行情。")

    while True:
        df = get_okx_klines()
        if df is None or df.empty:
            print("❌ 获取数据失败或数据为空，跳过本次计算")
            time.sleep(60)
            continue
        df = calculate_rsi(df)
        check_rsi(df)
        print("-" * 50)
        time.sleep(60)


if __name__ == "__main__":
    main()