import os
import time
from typing import Dict, Any, Optional, Tuple

import tushare as ts
import pandas as pd

TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")
if not TUSHARE_TOKEN:
    try:
        from config import TUSHARE_TOKEN as CONF_TOKEN  # type: ignore
        TUSHARE_TOKEN = CONF_TOKEN
    except Exception:
        TUSHARE_TOKEN = None

if TUSHARE_TOKEN:
    pro = ts.pro_api(TUSHARE_TOKEN)
else:
    pro = None


class TushareNotConfigured(Exception):
    """在未配置 Token 时调用需要 pro_api 的接口抛出。"""


_cache: Dict[Tuple[str, str], Tuple[float, Any]] = {}
CACHE_TTL = {
    "stock_basic": 3600,
    "daily": 60,
    "moneyflow": 60,
}


def _cache_get(kind: str, key: str):
    now = time.time()
    ttl = CACHE_TTL.get(kind, 0)
    val = _cache.get((kind, key))
    if not val:
        return None
    ts0, data = val
    if ttl and now - ts0 > ttl:
        return None
    return data


def _cache_set(kind: str, key: str, data: Any):
    _cache[(kind, key)] = (time.time(), data)


def get_realtime_quote(ts_code: str) -> pd.DataFrame:
    if not ts_code:
        raise ValueError("ts_code 不能为空，例如：000001.SZ")
    df = ts.realtime_quote(ts_code=ts_code)
    if df is None:
        return pd.DataFrame()
    return df


def get_history_daily(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    if pro is None:
        raise TushareNotConfigured(
            "未配置 TUSHARE_TOKEN，请设置环境变量或 config.py 中的 TUSHARE_TOKEN。"
        )
    if not ts_code:
        raise ValueError("ts_code 不能为空")
    params: Dict[str, Any] = {"ts_code": ts_code}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    key = f"{ts_code}-{start_date}-{end_date}"
    cached = _cache_get("daily", key)
    if cached is not None:
        return cached

    df = pro.daily(**params)  # type: ignore[arg-type]
    if df is None:
        df = pd.DataFrame()
    _cache_set("daily", key, df)
    return df


def get_moneyflow_batch(ts_codes: list[str]) -> pd.DataFrame:
    if pro is None:
        raise TushareNotConfigured(
            "未配置 TUSHARE_TOKEN，请设置环境变量或 config.py 中的 TUSHARE_TOKEN。"
        )
    if not ts_codes:
        return pd.DataFrame()

    key = ",".join(sorted(ts_codes))
    cached = _cache_get("moneyflow", key)
    if cached is not None:
        return cached

    dfs = []
    for code in ts_codes:
        try:
            df = pro.moneyflow(ts_code=code, limit=1)
            if df is not None and not df.empty:
                df = df.copy()
                df["ts_code"] = code
                dfs.append(df)
        except Exception:
            continue

    if dfs:
        all_df = pd.concat(dfs, ignore_index=True)
    else:
        all_df = pd.DataFrame()

    for col in [
        "buy_lg_amount",
        "buy_elg_amount",
        "sell_lg_amount",
        "sell_elg_amount",
    ]:
        if col not in all_df.columns:
            _cache_set("moneyflow", key, all_df)
            return all_df

    all_df["main_net_amount"] = (
        all_df["buy_lg_amount"]
        + all_df["buy_elg_amount"]
        - all_df["sell_lg_amount"]
        - all_df["sell_elg_amount"]
    )
    _cache_set("moneyflow", key, all_df)
    return all_df


def get_stock_basic() -> pd.DataFrame:
    if pro is None:
        raise TushareNotConfigured(
            "未配置 TUSHARE_TOKEN，请设置环境变量或 config.py 中的 TUSHARE_TOKEN。"
        )
    cached = _cache_get("stock_basic", "all")
    if cached is not None:
        return cached
    df = pro.stock_basic(
        exchange="",
        list_status="L",
        fields="ts_code,symbol,name,fullname,cnspell,market"
    )
    if df is None:
        df = pd.DataFrame()
    _cache_set("stock_basic", "all", df)
    return df
