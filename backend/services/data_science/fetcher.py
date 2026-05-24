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

    # ── 1. 缺失值處理 (Missing Value Handling) ──────────────────────────
    # 向前填補最多 3 天（跨市場假日、停牌）
    df = df.ffill(limit=3)
    # 移除超過半數欄位仍為 NaN 的列
    df = df.dropna(thresh=max(1, len(df.columns) // 2))

    # ── 2. 重複值處理 (Duplicate Removal) ──────────────────────────────
    df = df[~df.index.duplicated(keep="last")]

    return df.sort_index()


def remove_outliers_iqr(returns: pd.DataFrame, k: float = 5.0) -> pd.DataFrame:
    """
    異常值處理 (Outlier Handling) — IQR 截斷法

    金融報酬率中，極端值（如熔斷、閃崩）可能干擾模型訓練。
    使用 IQR（四分位距）方法：
      下界 = Q1 - k * IQR
      上界 = Q3 + k * IQR
    超出範圍的值用邊界值替換（Winsorize），而非直接刪除。
    k=5 比 k=1.5 寬鬆，保留更多金融極端事件但移除明顯錯誤資料。

    注意：只在訓練集計算 Q1/Q3，測試集使用相同邊界 → 防止洩漏。
    """
    result = returns.copy()
    bounds = {}  # 儲存每欄的邊界（供測試集使用）

    for col in result.columns:
        q1 = result[col].quantile(0.25)
        q3 = result[col].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - k * iqr
        upper = q3 + k * iqr
        bounds[col] = (lower, upper)

        n_before = result[col].isna().sum()
        result[col] = result[col].clip(lower=lower, upper=upper)
        n_clipped = ((returns[col] < lower) | (returns[col] > upper)).sum()

        if n_clipped > 0:
            print(f"  [Outlier] {col}: 截斷 {n_clipped} 個異常值 "
                  f"(範圍: [{lower:.4f}, {upper:.4f}])")

    return result, bounds


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
