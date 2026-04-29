import requests
import datetime
import time
import hmac
import hashlib
import base64
import os

print("SCHEDULE RUNNING")

# ====== Secrets ======
WEBHOOK = os.environ["FEISHU_WEBHOOK"]
SECRET = os.environ["FEISHU_SECRET"]
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]

# ====== ETF监控列表 ======
ETF_LIST = {
    "561380":"电网设备",
    "159608":"稀有金属ETF",
    "881281":"电池",
    "562590":"半导体设备",
    "159941": "纳指ETF",
    "159801": "芯片ETF",
    "159995": "半导体ETF",
    "518880": "黄金ETF",
    
}


# ====== 获取涨跌幅 ======
def get_realtime_change(code):

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    if code.startswith("88"):
        url = f"https://qt.gtimg.cn/q={code}"
    elif code.startswith("5"):
        url = f"https://qt.gtimg.cn/q=sh{code}"
    else:
        url = f"https://qt.gtimg.cn/q=sz{code}"

    try:

        r = requests.get(url, headers=headers, timeout=10)

        text = r.text
        data = text.split("=")[1].strip('";')
        fields = data.split("~")

        # ===== 板块指数 =====
        if code.startswith("88"):
            pct = float(fields[3])   # 板块涨跌幅

        # ===== ETF / 股票 =====
        else:
            pct = float(fields[32])

        return pct

    except Exception as e:

        print("获取失败:", code, e)
        return None


# ====== DeepSeek AI分析 ======
def ai_analysis(text):

    if not DEEPSEEK_API_KEY:
        return "未配置 AI KEY"

    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
根据以下ETF行情写一句简短市场分析：

{text}

要求：
1 不超过40字
2 像金融分析师点评
"""

    data = {
        "model": "deepseek-r1",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:

        r = requests.post(url, headers=headers, json=data)

        res = r.json()

        return res["choices"][0]["message"]["content"]

    except Exception as e:

        print("AI分析失败:", e)

        return "AI分析失败"


# ====== 飞书签名 ======
def gen_sign(timestamp, secret):

    string_to_sign = f"{timestamp}\n{secret}"

    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()

    return base64.b64encode(hmac_code).decode("utf-8")


# ====== 飞书推送 ======
def send_feishu(msg):

    timestamp = str(int(time.time()))

    sign = gen_sign(timestamp, SECRET)

    data = {
        "timestamp": timestamp,
        "sign": sign,
        "msg_type": "text",
        "content": {
            "text": msg
        }
    }

    r = requests.post(WEBHOOK, json=data)

    print(r.text)


# ====== 主程序 ======
def main():

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    result = []

    for code, name in ETF_LIST.items():

        pct = get_realtime_change(code)

        if pct is None:
            continue

        result.append((name, pct))

    # ===== 排序（跌幅排行）=====
    result.sort(key=lambda x: x[1])

    message = f"📊 {today} 14:30 ETF行情播报\n\n"

    alert_list = []

    for name, pct in result:

        if pct > 0:
            direction = "📈"
        elif pct < 0:
            direction = "📉"
        else:
            direction = "⏸"

        message += f"{name} {direction} {pct:.2f}%\n"

        if pct <= -3:
            alert_list.append((name, pct))

    # ===== 跌幅报警 =====
    if alert_list:

        message += "\n⚠️ 跌幅超过3%\n"

        for name, pct in alert_list:

            message += f"{name} {pct:.2f}%\n"

    # ===== AI分析 =====
    ai_text = ai_analysis(message)

    message += "\n🤖 AI行情分析\n"
    message += ai_text

    send_feishu(message)


if __name__ == "__main__":
    main()
