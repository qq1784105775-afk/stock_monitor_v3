from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)


# ========= 示例数据函数 =========

def get_realtime_quote(ts_codes):
    data = {}
    for code in ts_codes:
        data[code] = {
            "name": code,
            "cur": 10.0,
            "prev": 9.8
        }
    return data


def get_history5d(ts_code):
    return {
        "timestamp": [1, 2, 3, 4, 5],
        "indicators": {
            "quote": [{
                "close": [9.8, 9.9, 10.0, 10.1, 10.2],
                "volume": [1000, 1200, 1300, 1400, 1500]
            }]
        }
    }


def get_moneyflow(ts_codes):
    data = {}
    for code in ts_codes:
        data[code] = {
            "main_net_amount": 500000  # 示例
        }
    return data


def search_stock(keyword):
    # 假搜索
    return [{"ts_code": "002142.SZ"}]


# ========= API 路由 =========

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
def api_moneyflow():
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
        result = search_stock(q)
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ========= 首页（必须有） =========
@app.route("/")
def index():
    return "Backend is running."


# ========= Render 启动 =========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
