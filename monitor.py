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
SECRET = os.environ.get("FEISHU_SECRET", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

REQUEST_TIMEOUT = 10
BEIJING_TZ = datetime.timezone(datetime.timedelta(hours=8))

# ====== A股 / ETF / 板块监控列表 ======
WATCH_LIST = [
    {"code": "561380", "name": "电网设备", "type": "etf"},
    {"code": "159608", "name": "稀有金属ETF", "type": "etf"},
    {"code": "159755", "name": "电池广发ETF", "type": "etf"},
    {"code": "562590", "name": "半导体设备", "type": "etf"},
    {"code": "159941", "name": "纳指ETF", "type": "etf"},
    {"code": "159801", "name": "芯片ETF", "type": "etf"},
    {"code": "159995", "name": "半导体ETF", "type": "etf"},
    {"code": "518880", "name": "黄金ETF", "type": "etf"},
]


def build_quote_symbol(code, item_type):
    if item_type == "sector" or code.startswith("88"):
        return code
    if code.startswith(("5", "6", "9")):
        return f"sh{code}"
    if code.startswith(("0", "1", "2", "3")):
        return f"sz{code}"
    if code.startswith(("4", "8")):
        return f"bj{code}"
    raise ValueError(f"无法识别交易所前缀: {code}")


def parse_pct_change(code, item_type, fields):
    if item_type == "sector" or code.startswith("88"):
        return float(fields[3])
    return float(fields[32])


# ====== 获取涨跌幅 ======
def get_realtime_change(item):
    code = item["code"]
    item_type = item["type"]

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    symbol = build_quote_symbol(code, item_type)
    url = f"https://qt.gtimg.cn/q={symbol}"

    try:
        r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()

        text = r.text
        if "=" not in text:
            raise ValueError(f"行情返回格式异常: {text[:80]}")

        data = text.split("=", 1)[1].strip('";')
        if not data:
            raise ValueError("行情返回为空")

        fields = data.split("~")
        pct = parse_pct_change(code, item_type, fields)

        return {
            "code": code,
            "name": item["name"],
            "type": item_type,
            "pct": pct,
        }

    except Exception as e:
        print("获取失败:", code, e)
        return None


# ====== DeepSeek AI分析 ======
def ai_analysis(text):

    if not DEEPSEEK_API_KEY:
        return ""

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
        r = requests.post(url, headers=headers, json=data, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()

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

    data = {
        "msg_type": "text",
        "content": {
            "text": msg
        }
    }

    if SECRET:
        data["timestamp"] = timestamp
        data["sign"] = gen_sign(timestamp, SECRET)

    r = requests.post(WEBHOOK, json=data, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()

    print(r.text)


# ====== 主程序 ======
def main():

    today = datetime.datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")

    result = []
    failed_list = []

    for item in WATCH_LIST:

        quote = get_realtime_change(item)

        if quote is None:
            failed_list.append(f"{item['name']}({item['code']})")
            continue

        result.append(quote)

    # ===== 排序（跌幅排行）=====
    result.sort(key=lambda x: x["pct"])

    message = f"📊 {today} 14:30 A股行情播报\n\n"

    alert_list = []

    for item in result:
        name = item["name"]
        pct = item["pct"]

        if pct > 0:
            direction = "📈"
        elif pct < 0:
            direction = "📉"
        else:
            direction = "⏸"

        message += f"{name} {direction} {pct:.2f}%\n"

        if pct <= -3:
            alert_list.append(item)

    if failed_list:
        message += "\n⚠️ 获取失败\n"
        message += "\n".join(failed_list) + "\n"

    # ===== 跌幅报警 =====
    if alert_list:

        message += "\n⚠️ 跌幅超过3%\n"

        for item in alert_list:
            message += f"{item['name']} {item['pct']:.2f}%\n"

    # ===== AI分析 =====
    ai_text = ai_analysis(message)

    if ai_text:
        message += "\n🤖 AI行情分析\n"
        message += ai_text

    send_feishu(message)


if __name__ == "__main__":
    main()
