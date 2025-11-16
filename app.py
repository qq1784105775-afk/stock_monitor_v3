from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf


app = Flask(__name__)
CORS(app)


# --------------------------------------------------
#  实时快照批量接口  /api/snapshot_batch
# --------------------------------------------------
@app.route("/api/snapshot_batch")
def api_snapshot_batch():
    ts_codes = request.args.get("ts_codes", "")
    ts_codes = ts_codes.split(",") if ts_codes else []

    data = {}
    try:
        for code in ts_codes:
            ticker = yf.Ticker(code.replace(".SS", ".SS").replace(".SZ", ".SZ"))
            info = ticker.info

            data[code] = {
                "name": info.get("shortName"),
                "cur": info.get("regularMarketPrice"),
                "prev": info.get("regularMarketPreviousClose")
            }

        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# --------------------------------------------------
#  5日历史数据  /api/history5d
# --------------------------------------------------
@app.route("/api/history5d")
def api_history5d():
    ts_code = request.args.get("ts_code", "")
    if not ts_code:
        return jsonify({"ok": False, "error": "missing ts_code"})

    try:
        ticker = yf.Ticker(ts_code)
        hist = ticker.history(period="5d", interval="1d")

        return jsonify({
            "ok": True,
            "data": {
                "timestamp": [int(t.timestamp()) for t in hist.index],
                "indicators": {
                    "quote": [{
                        "close": list(hist["Close"]),
                        "volume": list(hist["Volume"]),
                    }]
                }
            }
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# --------------------------------------------------
#  主力资金接口（Mock）   /api/moneyflow_latest
# --------------------------------------------------
@app.route("/api/moneyflow_latest")
def api_moneyflow_latest():
    ts_codes = request.args.get("ts_codes", "")
    ts_codes = ts_codes.split(",") if ts_codes else []
    data = {}

    # 这里你可以换成真实数据源
    for code in ts_codes:
        data[code] = {
            "main_net_amount": 0
        }

    return jsonify({"ok": True, "data": data})


# --------------------------------------------------
# 首页路由
# --------------------------------------------------
@app.route("/")
def index():
    return "Backend Running OK", 200


# --------------------------------------------------
# Render 启动要求
# --------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
