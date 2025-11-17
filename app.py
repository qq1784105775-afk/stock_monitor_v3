from flask import Flask, request, jsonify
from tushare_service import (
    get_realtime_quote,
    get_history_5d,
    get_moneyflow_latest,
    search_stock
)

app = Flask(__name__)

@app.route("/api/snapshot_batch")
def api_snapshot_batch():
    ts_codes = request.args.get("ts_codes", "")
    ts_codes = ts_codes.split(",") if ts_codes else []
    try:
        df = get_realtime_quote(ts_codes)
        return jsonify({"ok": True, "data": df.to_dict(orient="index")})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/history5d")
def api_history5d():
    ts_code = request.args.get("ts_code")
    if not ts_code:
        return jsonify({"ok": False, "error": "ts_code missing"})
    try:
        data = get_history_5d(ts_code)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/moneyflow_latest")
def api_moneyflow_latest():
    ts_codes = request.args.get("ts_codes", "")
    ts_codes = ts_codes.split(",") if ts_codes else []
    try:
        data = get_moneyflow_latest(ts_codes)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/search_stock")
def api_search_stock():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"ok": False, "error": "empty query"})
    try:
        data = search_stock(q)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/")
def home():
    return "Stock Monitor V3.1 Backend OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
