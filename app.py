from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ===== 工具函数 =====

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
                "close": [9.8, 9.9, 10.0, 10.2, 10.3],
                "volume": [1000, 1200, 1100, 1300, 1250]
            }]
        }
    }

# ===== API 路由 =====

@app.route("/")
def home():
    return jsonify({"ok": True, "msg": "service running"}), 200


@app.route("/api/snapshot_batch")
def api_snapshot_batch():
    ts_codes = request.args.get("ts_codes", "")
    ts_codes = ts_codes.split(",") if ts_codes else []

    try:
        data = get_realtime_quote(ts_codes)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/history5d")
def api_history5d():
    ts_code = request.args.get("ts_code", "")
    if not ts_code:
        return jsonify({"ok": False, "error": "ts_code required"}), 400

    try:
        data = get_history5d(ts_code)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
