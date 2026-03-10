import requests
import datetime
import time
import hmac
import hashlib
import base64
import os

# ====== 从 GitHub Secrets 读取 ======
print("SCHEDULE RUNNING")
WEBHOOK = os.environ["FEISHU_WEBHOOK"]
SECRET = os.environ["FEISHU_SECRET"]

ETF_LIST = {
    "886078": "商业航天",
    "159227": "航空航天发展ETF",
    "159941": "纳指ETF",
    "159801": "芯片ETF",
    "159995": "半导体ETF",
    "518880": "黄金ETF"
}


def get_realtime_change(code):

    url = f"https://d.10jqka.com.cn/v6/realhead/{code}.json"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)

        data = r.json()

        # 同花顺字段
        pct = float(data["items"]["chg"])   # 涨跌幅

        return pct

    except Exception as e:
        print("获取失败:", code, e)
        return None


def gen_sign(timestamp, secret):
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


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


def main():

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    message = f"📊 {today} 14:30 ETF行情播报\n\n"

    for code, name in ETF_LIST.items():

        pct = get_realtime_change(code)

        if pct is None:
            message += f"{name} 获取失败\n"
            continue

        if pct > 0:
            direction = "📈 上涨"
        elif pct < 0:
            direction = "📉 下跌"
        else:
            direction = "⏸ 平盘"

        message += f"{name} {direction} {pct:.2f}%\n"

    send_feishu(message)


if __name__ == "__main__":
    main()
