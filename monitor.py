import requests
import datetime

# ====== 你的飞书机器人 Webhook ======
WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/dpdtDM5jkBzefb0G6v3JUh"

# ====== 监控的 ETF 列表 ======
ETF_LIST = {
    "159227": "航空航天ETF",
    "159941": "纳指ETF",
    "159801": "芯片ETF",
    "159995": "半导体ETF",
    "518880": "黄金ETF"
}


def get_realtime_change(code):
    # 判断市场
    if code.startswith("5"):
        market = "sh"
    else:
        market = "sz"

    url = f"https://qt.gtimg.cn/q={market}{code}"

    try:
        r = requests.get(url, timeout=10)
        text = r.text

        if "=" not in text:
            return None

        data = text.split("=")[1].strip('";\n')
        fields = data.split("~")

        if len(fields) < 33:
            return None

        pct = float(fields[32])
        return pct

    except Exception:
        return None


def send_feishu(msg):
    data = {
        "msg_type": "text",
        "content": {
            "text": msg
        }
    }
    requests.post(WEBHOOK, json=data)


def main():
    now = datetime.datetime.now()
    today = now.strftime("%Y-%m-%d")

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
