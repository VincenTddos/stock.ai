"""
fetcher.py — 多股票資料抓取與對齊
支援台股（.TW 後綴）與美股，統一對齊到相同交易日
"""
import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Dict


DEFAULT_INDICES = {
    "^TWII": "台灣加權指數",
    "^GSPC": "S&P 500",
    "^IXIC": "NASDAQ",
    "^VIX":  "VIX 恐慌指數",
}


def fetch_prices(tickers: List[str], period: str = "3y") -> pd.DataFrame:
    """
    抓取多支股票的每日收盤價，對齊到共同交易日（取聯集，缺值向前填補）。
    回傳 DataFrame，欄位為 ticker，index 為日期。
    """
    frames = {}
    for t in tickers:
        try:
            raw = yf.Ticker(t).history(period=period, auto_adjust=True)
            if raw.empty:
                continue
            frames[t] = raw["Close"].rename(t)
        except Exception:
            continue

    if not frames:
        raise ValueError("無法取得任何股票資料，請確認代號正確。")

    df = pd.concat(frames.values(), axis=1)
    df.index = pd.to_datetime(df.index).tz_localize(None)  # 移除時區

    # 向前填補（最多 3 天），避免跨市場假日造成大量 NaN
    df = df.ffill(limit=3)

    # 移除超過半數欄位都是 NaN 的列（通常是節日）
    df = df.dropna(thresh=max(1, len(df.columns) // 2))

    return df.sort_index()


def compute_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """
    計算對數報酬率：log(P_t / P_{t-1})
    優點：
      - 時間可加性（各期報酬可直接相加）
      - 近似常態分布
      - 天然正規化（去除價格水準差異）
    """
    log_ret = np.log(prices / prices.shift(1))
    return log_ret.dropna(how="all")


def align_tw_us(tw_tickers: List[str], us_tickers: List[str],
                period: str = "3y") -> Dict[str, pd.DataFrame]:
    """
    抓取台股與美股，分別計算對數報酬率，並對齊到共同日期。
    回傳 dict：
      - 'prices'    : 收盤價 DataFrame
      - 'returns'   : 對數報酬率 DataFrame
      - 'tw_cols'   : 台股欄位名稱列表
      - 'us_cols'   : 美股欄位名稱列表
    """
    all_tickers = list(dict.fromkeys(tw_tickers + us_tickers))  # 去重、保持順序
    prices = fetch_prices(all_tickers, period)
    returns = compute_log_returns(prices)

    # 只保留實際有資料的欄位
    tw_cols = [t for t in tw_tickers if t in returns.columns]
    us_cols = [t for t in us_tickers if t in returns.columns]

    return {
        "prices": prices,
        "returns": returns,
        "tw_cols": tw_cols,
        "us_cols": us_cols,
    }
