import os
from datetime import datetime, timedelta

import pandas as pd
from flask import Flask, jsonify, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

from tushare_service import (
    get_realtime_quote,
    get_history_daily,
    get_moneyflow_batch,
    get_stock_basic,
    TushareNotConfigured,
    pro,
)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)


# ---------------- 工具函数 ----------------

def df_to_records(df: pd.DataFrame):
    if df is None or df.empty:
        return []
    return df.where(pd.notnull(df), None).to_dict(orient="records")


# ---------------- 前端主页 ----------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------- 实时数据接口 ----------------
@app.route("/api/snapshot_batch")
def api_snapshot_batch():
    ts_codes_str = request.args.get("ts_codes", "").strip()
    if not ts_codes_str:
        return jsonify({"ok": True, "data": {}})

    codes = [c.strip() for c in ts_codes_str.split(",") if c.strip()]
    data = {}

    for code in codes:
        try:
            df = get_realtime_quote(code)
            if df is None or df.empty:
                continue
            row = df.iloc[0]

            # 名称
            name = row.get("name") or row.get("ts_name") or code

            # 昨收价
            prev = None
            for col in ["pre_close", "preclose", "last_close", "close_yest"]:
                if col in df.columns:
                    prev = float(row.get(col) or 0)
                    break
            if prev is None:
                prev = float(row.get("close") or row.get("price") or row.get("last") or 0)

            # 当前价
            cur = None
            for col in ["price", "last", "close", "trade"]:
                if col in df.columns:
                    cur = float(row.get(col) or 0)
                    break
            if cur is None:
                cur = prev

            # 成交量
            vol = 0.0
            for col in ["vol", "volume", "amount"]:
                if col in df.columns:
                    vol = float(row.get(col) or 0)
                    break

            high = None
            for col in ["high", "high_price"]:
                if col in df.columns:
                    high = float(row.get(col) or 0)
                    break

            low = None
            for col in ["low", "low_price"]:
                if col in df.columns:
                    low = float(row.get(col) or 0)
                    break

            data[code] = {
                "name": name,
                "prev": prev,
                "cur": cur,
                "vol": vol,
                "high": high,
                "low": low,
            }
        except Exception:
            continue

    return jsonify({"ok": True, "data": data})


# ---------------- 5日历史接口 ----------------
@app.route("/api/history5d")
def api_history5d():
    ts_code = request.args.get("ts_code", "").strip()
    if not ts_code:
        return jsonify({"ok": False, "error": "ts_code required"}), 400

    if pro is None:
        return jsonify({"ok": False, "error": "Tushare 未配置"}), 500

    try:
        end = datetime.today()
        start = end - timedelta(days=10)

        df = get_history_daily(
            ts_code=ts_code,
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
        )

        if df is None or df.empty:
            return jsonify({"ok": False, "error": "无历史数据"}), 200

        df = df.sort_values("trade_date").tail(5)

        closes = df["close"].tolist()
        volumes = (df["vol"] * 100).tolist() if "vol" in df.columns else df.get("amount", df["close"]).tolist()
        timestamps = [int(datetime.strptime(d, "%Y%m%d").timestamp()) for d in df["trade_date"]]

        data = {
            "indicators": {
                "quote": [{
                    "close": closes,
                    "volume": volumes,
                }]
            },
            "timestamp": timestamps,
        }
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ---------------- 主力资金接口 ----------------
@app.route("/api/moneyflow_latest")
def api_moneyflow_latest():
    ts_codes_str = request.args.get("ts_codes", "").strip()
    if not ts_codes_str:
        return jsonify({"ok": True, "data": {}})

    if pro is None:
        return jsonify({"ok": False, "error": "Tushare 未配置"}), 500

    codes = [c.strip() for c in ts_codes_str.split(",") if c.strip()]

    try:
        df = get_moneyflow_batch(codes)
        if df is None or df.empty:
            return jsonify({"ok": True, "data": {}})

        df = df.sort_values(["ts_code", "trade_date"])
        latest = df.groupby("ts_code").tail(1)
        result = {}

        for _, row in latest.iterrows():
            code = row["ts_code"]
            result[code] = {
                "trade_date": row.get("trade_date"),
                "buy_lg_amount": row.get("buy_lg_amount"),
                "buy_elg_amount": row.get("buy_elg_amount"),
                "sell_lg_amount": row.get("sell_lg_amount"),
                "sell_elg_amount": row.get("sell_elg_amount"),
                "main_net_amount": row.get("main_net_amount"),
            }

        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ---------------- 股票搜索 ----------------
@app.route("/api/search_stock")
def api_search_stock():
    if pro is None:
        return jsonify({"ok": False, "error": "Tushare 未配置"}), 500

    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"ok": True, "data": []})

    try:
        df = get_stock_basic()
        if df is None or df.empty:
            return jsonify({"ok": True, "data": []})

        q_low = q.lower()
        q_up = q.upper()

        cond = (
            df["ts_code"].str.contains(q_up, case=False, na=False)
            | df["symbol"].str.contains(q_up, case=False, na=False)
            | df["name"].str.contains(q, case=False, na=False)
        )
        if "fullname" in df.columns:
            cond |= df["fullname"].str.contains(q, case=False, na=False)
        if "cnspell" in df.columns:
            cond |= df["cnspell"].str.contains(q_low, case=False, na=False)

        return jsonify({"ok": True, "data": df[cond].head(20).to_dict(orient="records")})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ---------------- 健康检测 ----------------
@app.route("/api/ping")
def api_ping():
    return jsonify({"ok": True, "time": datetime.utcnow().isoformat() + "Z"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
