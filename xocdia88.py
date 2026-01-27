from flask import Flask, jsonify
import threading, websocket, json, time, os
from collections import deque

app = Flask(__name__)

# ================= CẤU HÌNH =================
WS_URL = "wss://taixiumd5.system32-cloudfare-356783752985678522.monster/signalr/reconnect?transport=webSockets&connectionToken=SgIYXqnbkJRw6FvkcaXYVrAcj9Rkcx758qlxIanF3odMFBbrqY%2BJJ%2FVvZUnOX0Z2pNFJwckC2pCxXefKhAclClEefIExyEGKc9Z6zfoZsoa9oUAzcs1LNw2G3jxr7w9j&connectionData=%5B%7B%22name%22%3A%22md5luckydiceHub%22%7D%5D&tid=6&access_token=05%2F7JlwSPGzg4ARi0d7%2FLOcNQQ%2BecAvgB3UwDAmuWFJiZj%2Blw1TcJ0PZt5VeUAHKLVCmODRrV5CHPNbit3mc868w8zYBuyQ5Xlu1AZVsEElr9od2qJ8S9N2GLAdQnd0VL8fj8IAGPMsP45pdIIXZysKmRi40b%2FOVLAp4yOpkaXP3icyn2%2Fodm397vVKSY9AlMCcH15AghVm3lx5JM%2BoUuP%2Fkjgh5xWXtdTQkd9W3%2BQBY25AdX3CvOZ2I17r67METGpFv8cP7xmAoySWEnokU2IcOKu3mzvRWXsG7N5sHFkv%2FIKw%2F1IPCNY2oi8RygWpHwIFWcHGdeoTeM6kskfrqNSmhapPBCREit0So1HOC6jOiz5IyKVNadwp8EfsxKzBOKE0z0zdavvY6wXrSZhIJeIqKqVAt3SEuoG82a%2BjwxNo%3D.5a1d88795043d5c4ef6538c9edfb5ff93e65b852d89b71344bdd5ec80eb63e24"
HISTORY_LEN = 20
VER_LEN = 12

# ================= BIẾN =================
latest_result = {
    "phien": None,
    "xuc_xac_1": -1,
    "xuc_xac_2": -1,
    "xuc_xac_3": -1,
    "tong": -1,
    "ket_qua": None,
    "du_doan": "Chờ dữ liệu"
}

history = deque(maxlen=HISTORY_LEN)
lock = threading.Lock()

# ================= BẢNG VER =================
prediction_table = {
    "XXXXXXXXXTXXX": "Xỉu",
    "XXXXXXXXXXTTT": "Xỉu",
    "XXXXXXXXXXTTX": "Xỉu",
    "XXXXXXXXXXTXT": "Xỉu",
    "XXXXXXXXXXTXX": "Xỉu",
    "XXXXXXXXXXXTT": "Tài",
    "XXXXXXXXXXXTX": "Tài",
    "XXXXXXXXXXXXT": "Xỉu",
    "XXXXXXXXXXXXX": "Xỉu",
}

# ================= VER =================
def predict_ver():
    if len(history) < VER_LEN:
        return "Chờ dữ liệu"

    seq = "".join(history)[-VER_LEN:]

    if seq in prediction_table:
        return prediction_table[seq]

    for i in range(VER_LEN - 1, 2, -1):
        sub = seq[-i:]
        if sub in prediction_table:
            return prediction_table[sub]

    return "Tài" if history[-1] == "X" else "Xỉu"

# ================= SIGNALR =================
def on_message(ws, message):
    global latest_result

    for msg in message.split('\x1e'):
        if not msg:
            continue

        try:
            data = json.loads(msg)
            if "M" not in data:
                continue

            for item in data["M"]:
                if item.get("M") != "Md5sessionInfo":
                    continue

                info = item["A"][0]
                phien = info.get("SessionID")
                r = info.get("Result", {})

                d1 = r.get("Dice1")
                d2 = r.get("Dice2")
                d3 = r.get("Dice3")

                # ✅ CHỈ ĂN KHI CÓ ĐỦ 3 XÚC XẮC
                if not all(isinstance(x, int) and 1 <= x <= 6 for x in (d1, d2, d3)):
                    continue

                with lock:
                    if latest_result["phien"] == phien:
                        continue

                    tong = d1 + d2 + d3
                    ket_qua = "Tài" if tong >= 11 else "Xỉu"
                    history.append("T" if ket_qua == "Tài" else "X")

                    latest_result.update({
                        "phien": phien,
                        "xuc_xac_1": d1,
                        "xuc_xac_2": d2,
                        "xuc_xac_3": d3,
                        "tong": tong,
                        "ket_qua": ket_qua,
                        "du_doan": predict_ver()
                    })

                    print(f"✅ {phien} | {d1}-{d2}-{d3} | {ket_qua}")

        except Exception as e:
            print("WS error:", e)

def on_open(ws):
    # Handshake SignalR
    ws.send(json.dumps({
        "protocol": "json",
        "version": 1
    }) + "\x1e")

def start_ws():
    while True:
        try:
            ws = websocket.WebSocketApp(
                WS_URL,
                on_open=on_open,
                on_message=on_message
            )
            ws.run_forever(ping_interval=15, ping_timeout=5)
        except Exception as e:
            print("Reconnect WS:", e)
            time.sleep(3)

# ================= API =================
@app.route("/")
def home():
    return jsonify(latest_result)

@app.route("/api")
def api():
    with lock:
        return jsonify(latest_result)

@app.route("/history")
def api_history():
    with lock:
        return jsonify(list(history))

# ================= MAIN =================
if __name__ == "__main__":
    threading.Thread(target=start_ws, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
