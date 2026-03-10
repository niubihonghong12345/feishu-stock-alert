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

        pct = float(fields[32])

        return pct

    except Exception as e:

        print("获取失败:", code, e)

        return None
