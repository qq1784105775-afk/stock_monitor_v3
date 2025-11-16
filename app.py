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


def df_to_records(df: pd.DataFrame):
    if df is None or df.empty:
        return []
    return df.where(pd.notnull(df), None).to_dict(orient="records")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/snapshot_batch")
def api_snapshot_batch():
    """批量返回简化快照行情。"""
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

            name = row.get("name") or row.get("ts_name") or code

            prev = None
            for col in ["pre_close", "preclose", "preClose", "last_close", "close_yest"]:
                if col in df.columns:
                    prev = float(row.get(col) or 0)
                    break
            if prev is None:
                prev = float(row.get("close") or row.get("price") or row.get("last") or 0)

            cur = None
            for col in ["price", "last", "close", "trade"]:
                if col in df.columns:
                    cur = float(row.get(col) or 0)
                    break
            if cur is None:
                cur = prev

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


@app.route("/api/history5d")
def api_history5d():
    """返回 5 日历史数据，结构类似 Yahoo。"""
    ts_code = request.args.get("ts_code", "").strip()
    if not ts_code:
        return jsonify({"ok": False, "error": "ts_code is required"}), 400

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

        df = df.sort_values("trade_date")
        df = df.tail(5)

        closes = df["close"].tolist()
        if "vol" in df.columns:
            volumes = (df["vol"] * 100).tolist()
        else:
            volumes = df.get("amount", df["close"]).tolist()

        timestamps = [
            int(datetime.strptime(d, "%Y%m%d").timestamp())
            for d in df["trade_date"].tolist()
        ]

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


@app.route("/api/moneyflow_latest")
def api_moneyflow_latest():
    """批量获取多只股票最近一日资金流向（主力净额等）。"""
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
            code = row.get("ts_code")
            result[code] = {
                "trade_date": row.get("trade_date"),
                "buy_lg_amount": row.get("buy_lg_amount"),
                "buy_elg_amount": row.get("buy_elg_amount"),
                "sell_lg_amount": row.get("sell_lg_amount"),
                "sell_elg_amount": row.get("sell_elg_amount"),
                "main_net_amount": row.get("main_net_amount"),
            }
        return jsonify({"ok": True, "data": result})
    except TushareNotConfigured as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/search_stock")
def api_search_stock():
    """搜索 A 股股票（代码 / 名称 / 拼音 模糊匹配），用于前端添加监控。"""
    if pro is None:
        return jsonify({"ok": False, "error": "Tushare 未配置"}), 500

    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"ok": True, "data": []})

    try:
        df = get_stock_basic()
        if df is None or df.empty:
            return jsonify({"ok": True, "data": []})
        q_lower = q.lower()
        q_upper = q.upper()

        cond = (
            df["ts_code"].str.contains(q_upper, case=False, na=False)
            | df["symbol"].str.contains(q_upper, case=False, na=False)
            | df["name"].str.contains(q, case=False, na=False)
        )
        if "fullname" in df.columns:
            cond |= df["fullname"].str.contains(q, case=False, na=False)
        if "cnspell" in df.columns:
            cond |= df["cnspell"].str.contains(q_lower, case=False, na=False)

        sub = df[cond].head(20)
        records = sub.to_dict(orient="records")
        return jsonify({"ok": True, "data": records})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/zt_ranking")
def api_zt_ranking():
    """简单涨停强度榜。

    逻辑：根据当日涨幅接近 10% 且收盘价接近涨停价筛选，再按涨幅 + 换手率排序。
    """
    if pro is None:
        return jsonify({"ok": False, "error": "Tushare 未配置"}), 500

    trade_date = (request.args.get("trade_date") or "").strip()
    if not trade_date:
        trade_date = datetime.today().strftime("%Y%m%d")

    try:
        # 取当日所有日线数据
        daily = pro.daily(trade_date=trade_date)
        if daily is None or daily.empty:
            return jsonify({"ok": True, "data": []})

        # 涨停近似条件：涨幅 >= 9.5%
        daily = daily.copy()
        daily["pct_chg"] = (daily["close"] - daily["pre_close"]) / daily["pre_close"] * 100
        zt = daily[(daily["pct_chg"] >= 9.5)]

        if zt.empty:
            return jsonify({"ok": True, "data": []})

        # 引入换手率加强强度
        basic = get_stock_basic()
        merged = zt.merge(basic[["ts_code", "name"]], on="ts_code", how="left")

        def score_row(r):
            pct = float(r.get("pct_chg") or 0)
            vol = float(r.get("vol") or 0)
            # 简化强度分：涨幅 + 成交量因子（对数）
            import math
            vol_factor = math.log10(max(vol, 1))
            return pct + vol_factor * 2.0

        merged["strength"] = merged.apply(score_row, axis=1)
        merged = merged.sort_values("strength", ascending=False)
        top = merged.head(50)

        return jsonify({"ok": True, "data": df_to_records(top)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/ping")
def api_ping():
    return jsonify({"ok": True, "time": datetime.utcnow().isoformat() + "Z"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
