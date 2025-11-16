from flask import Flask, request, jsonify, send_from_directory
import requests
import os

app = Flask(__name__)

# ===== 工具函数 =====

def get_realtime_quote(ts_codes):
    # 示例数据（你也可以替换为自己的实时行情 API）
    data = {}
    for code in ts_codes:
        data[code] = {
            "name": code,
            "cur": 10.0,
            "prev": 9.8
        }
    return data

def get_history5d(ts_code):
    # 示例历史 K 线数据
    return {
        "timestamp": [1, 2, 3, 4, 5],
        "indicators": {
            "quote": [{
                "close": [9.8, 9.9, 10.0, 10.2, 10.3],
                "volume": [1000, 1200, 1300, 2000, 2500]
            }]
        }
    }

def get_moneyflow(ts_codes):
    data = {}
    for c in ts_codes:
        data[c] = {"main_net_amount": 123456}
    return data

def search_stock(keyword):
    return [{"ts_code": "600000.SS", "name": "浦发银行"}]

# ====== 路由 ======

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/api/snapshot_batch")
def api_snapshot_batch():
    ts_codes = request.args.get("ts_codes", "")
    ts_codes = ts_codes.split(",") if ts_codes else []
    try:
        df = get_realtime_quote(ts_codes)
        return jsonify({"ok": True, "data": df})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/history5d")
def api_history5d():
    code = request.args.get("ts_code", "")
    try:
        data = get_history5d(code)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/moneyflow_latest")
def api_moneyflow_latest():
    ts_codes = request.args.get("ts_codes", "")
    ts_codes = ts_codes.split(",") if ts_codes else []
    try:
        data = get_moneyflow(ts_codes)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/search_stock")
def api_search_stock():
    q = request.args.get("q", "")
    try:
        data = search_stock(q)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
