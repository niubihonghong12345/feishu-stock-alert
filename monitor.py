import requests
import time
import hmac
import hashlib
import base64
import akshare as ak
import os

WEBHOOK = os.environ.get("FEISHU_WEBHOOK")
SECRET = os.environ.get("FEISHU_SECRET")

ETF_LIST = {
    "半导体ETF": "159995",
    "航空航天ETF": "159227",
    "纳指ETF": "159941",
    "芯片ETF": "159801",
    "黄金ETF": "518880"
}

def sign_request(secret):
    timestamp = str(int(time.time()))
    string_to_sign = f'{timestamp}\n{secret}'
    hmac_code = hmac.new(
        secret.encode(),
        string_to_sign.encode(),
        digestmod=hashlib.sha256
    ).digest()
    sign = base64.b64encode(hmac_code).decode()
    return timestamp, sign

def send_feishu(msg):
    timestamp, sign = sign_request(SECRET)
    params = {"timestamp": timestamp, "sign": sign}
    data = {
        "msg_type": "text",
        "content": {"text": msg}
    }
    requests.post(WEBHOOK, params=params, json=data)

def get_realtime_change(code):
    df = ak.stock_zh_a_spot_em()
    row = df[df["代码"] == code]
    if not row.empty:
        return float(row.iloc[0]["涨跌幅"])
    return None

def main():
    message = "📊 14:30 ETF 实时涨跌幅提醒\n\n"
    for name, code in ETF_LIST.items():
        pct = get_realtime_change(code)
        if pct is not None:
            message += f"{name}（{code}）：{pct}%\n"
        else:
            message += f"{name}（{code}）：获取失败\n"

    send_feishu(message)

if __name__ == "__main__":
    main()