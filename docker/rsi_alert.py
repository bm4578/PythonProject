import requests
import pandas as pd
import ta
import time

# 钉钉机器人 Webhook 地址
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
    headers = {"User-Agent": "Mozilla/5.0"}
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

def calculate_indicators(df, rsi_period=14, ema_period=20):
    if df is None or len(df) < max(rsi_period, ema_period) + 1:
        print("⚠️ 数据不足，无法计算指标")
        return None
    # RSI
    df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=rsi_period).rsi()
    # EMA
    df['ema'] = ta.trend.EMAIndicator(close=df['close'], window=ema_period).ema_indicator()
    # MACD
    macd = ta.trend.MACD(close=df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff'] = macd.macd_diff()
    return df

# 全局状态
last_state = {
    "rsi_overbought": None,
    "rsi_oversold": None,
    "macd_cross": None,  # True 表示 macd金叉，False表示死叉，None表示未判断
}

def check_indicators(df):
    global last_state
    if df is None or df.empty:
        print("⚠️ 数据不足，无法判断")
        return

    latest = df.iloc[-1]
    latest_rsi = latest['rsi']
    latest_price = latest['close']
    latest_ema = latest['ema']
    latest_macd = latest['macd']
    latest_macd_signal = latest['macd_signal']

    print(f"当前 5分钟 RSI：{latest_rsi:.2f}，价格：{latest_price:.2f}，EMA：{latest_ema:.2f}")

    # 判断MACD金叉死叉：上一根macd - signal，当前macd - signal
    prev = df.iloc[-2]
    prev_macd_diff = prev['macd'] - prev['macd_signal']
    curr_macd_diff = latest_macd - latest_macd_signal

    macd_cross = None
    if prev_macd_diff <= 0 and curr_macd_diff > 0:
        macd_cross = True  # 金叉
    elif prev_macd_diff >= 0 and curr_macd_diff < 0:
        macd_cross = False  # 死叉

    # 结合 RSI 超买超卖和MACD交叉判断报警
    # 超买 + MACD死叉 -> 卖出信号
    if last_state["rsi_overbought"] is None:
        last_state["rsi_overbought"] = latest_rsi > 70
    else:
        if not last_state["rsi_overbought"] and latest_rsi > 70:
            last_state["rsi_overbought"] = True
        elif last_state["rsi_overbought"] and latest_rsi <= 70:
            last_state["rsi_overbought"] = False

    # 超卖 + MACD金叉 -> 买入信号
    if last_state["rsi_oversold"] is None:
        last_state["rsi_oversold"] = latest_rsi < 30
    else:
        if not last_state["rsi_oversold"] and latest_rsi < 30:
            last_state["rsi_oversold"] = True
        elif last_state["rsi_oversold"] and latest_rsi >= 30:
            last_state["rsi_oversold"] = False

    # MACD状态更新
    if last_state["macd_cross"] is None:
        last_state["macd_cross"] = macd_cross
    else:
        if macd_cross is not None and macd_cross != last_state["macd_cross"]:
            last_state["macd_cross"] = macd_cross

    # 联合判断发报警
    # 卖出信号：RSI上穿70且MACD死叉
    if last_state["rsi_overbought"] and macd_cross is False:
        print("⚠️ RSI超买且MACD死叉，可能卖出信号")
        send_ding_alert(f"⚠️ 卖出信号！RSI {latest_rsi:.2f}，MACD死叉，价格 {latest_price:.2f}")

    # 买入信号：RSI下穿30且MACD金叉
    elif last_state["rsi_oversold"] and macd_cross is True:
        print("⚠️ RSI超卖且MACD金叉，可能买入信号")
        send_ding_alert(f"⚠️ 买入信号！RSI {latest_rsi:.2f}，MACD金叉，价格 {latest_price:.2f}")

    else:
        print("指标正常，无报警")

def main():
    send_ding_alert("✅ RSI+EMA+MACD监控脚本已启动，开始实时监控市场行情。")

    while True:
        df = get_okx_klines()
        if df is None or df.empty:
            print("❌ 获取数据失败或数据为空，跳过本次计算")
            time.sleep(60)
            continue
        df = calculate_indicators(df)
        check_indicators(df)
        print("-" * 50)
        time.sleep(60)

if __name__ == "__main__":
    main()
