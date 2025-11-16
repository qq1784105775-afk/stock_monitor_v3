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

            # 昨收
            prev = None
            for col in ["pre_close", "preclose", "preClose", "last_close"]:
                if col in df.columns:
                    prev = float(row.get(col) or 0)
                    break
            if prev is None:
                prev = float(row.get("close") or row.get("price") or row.get("last") or 0)

            # 最新价
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

            # 最高
            high = None
            for col in ["high", "high_price"]:
                if col in df.columns:
                    high = float(row.get(col) or 0)
                    break

            # 最低
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
