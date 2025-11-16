from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# ================ 示例函数：你自己的行情接口 ==================
# 你之前引用了 get_realtime_quote / history5d / moneyflow，这里要补齐
# 现在给你写个可运行的最简版，你喜欢再换成你自己的数据源

def get_realtime_quote(ts_codes):
    # ⚠️ 临时假数据（避免你的前端崩溃）
    data = {}
    for code in ts_codes:
        data[code] = {
            "name": code,
            "cur": 10.0,
            "prev": 9.8
        }
    return data

def get_history5d(ts_code):
    # 返回简单的空结构，避免前端报错
    return {
        "timestamp": [],
        "indicators": {"quote": [{"close": [], "volume": []}]}
    }

def get_moneyflow(ts_codes):
    return {code: {"main_net_amount": 0} for code in ts_codes}

# ============================================================

@app.route("/")
def index():
    return "Backend is running."

# ------- 你前端需要的正式 API ---------

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
    ts_code = request.args.get("ts_code", "")
    try:
        h = get_history5d(ts_code)
        return jsonify({"ok": True, "data": h})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/moneyflow_latest")
def api_moneyflow_latest():
    ts_codes = request.args.get("ts_codes", "")
    ts_codes = ts_codes.split(",") if ts_codes else []
    try:
        mf = get_moneyflow(ts_codes)
        return jsonify({"ok": True, "data": mf})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
