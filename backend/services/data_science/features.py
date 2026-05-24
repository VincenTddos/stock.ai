"""
features.py — 特徵工程（嚴格防止資料洩漏）

核心原則：
  預測「今天的報酬方向」時，所有特徵只能使用「昨天以前」的資料。
  作法：所有特徵計算完後都必須 .shift(1)，確保不包含當天資訊。

合法的跨市場信號：
  美股週一收盤（美東時間 16:00）→ 台股週二開盤（台北時間 09:00）
  → 可以用美股當天收盤作為特徵預測台股隔天（不算洩漏）
  但為了統一與保守，本模組一律 shift(1)。
"""
import numpy as np
import pandas as pd
from typing import List


def _rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """計算相對強弱指標（RSI）"""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    return 100 - (100 / (1 + rs))


def build_features(
    returns: pd.DataFrame,
    target_col: str,
    feature_cols: List[str],
    lags: List[int] = [1, 2, 3, 5],
    vol_windows: List[int] = [5, 10, 20],
) -> pd.DataFrame:
    """
    建立特徵矩陣（無資料洩漏版本）。

    參數：
      returns      : 對數報酬率 DataFrame（所有股票）
      target_col   : 預測目標欄位（如 '2330.TW'）
      feature_cols : 用於預測的欄位（如 ['SPY', '^VIX', '^TWII']）
      lags         : 使用幾天前的報酬作為特徵
      vol_windows  : 滾動波動率窗口

    回傳：
      feature_df   : 特徵 DataFrame，已移除 NaN 列
    """
    all_cols = list(dict.fromkeys([target_col] + feature_cols))
    df = returns[all_cols].copy()

    feat = pd.DataFrame(index=df.index)

    for col in all_cols:
        # --- 落後報酬率 (Lagged Returns) ---
        # shift(1) = 使用昨天的報酬預測今天，嚴格無洩漏
        for lag in lags:
            feat[f"{col}_lag{lag}"] = df[col].shift(lag)

        # --- 滾動波動率 (Rolling Volatility) ---
        # shift(1) 再 rolling：確保計算窗口不包含當天
        for w in vol_windows:
            feat[f"{col}_vol{w}d"] = df[col].shift(1).rolling(w).std()

        # --- RSI (基於昨天以前的收盤報酬) ---
        rsi_vals = _rsi(df[col].shift(1))
        feat[f"{col}_rsi14"] = rsi_vals

        # --- 短期 vs 長期均線比值 (Momentum) ---
        # 使用 shift(1) 的滾動均值
        ma5  = df[col].shift(1).rolling(5).mean()
        ma20 = df[col].shift(1).rolling(20).mean()
        feat[f"{col}_ma5_20_ratio"] = ma5 / (ma20 + 1e-9)

    # --- 跨市場特徵：美股報酬對台股的影響 ---
    for us_col in [c for c in feature_cols if ".TW" not in c and "^TW" not in c]:
        for tw_col in [c for c in all_cols if ".TW" in c or "^TW" in c]:
            # 滾動相關係數（20天）
            roll_corr = df[us_col].shift(1).rolling(20).corr(df[tw_col].shift(1))
            feat[f"corr_{us_col}_{tw_col}_20d"] = roll_corr

    # --- 目標變數 ---
    # 今天報酬 > 0 → 1（上漲），否則 → 0（下跌）
    # 注意：target 是「當天」的資訊，只在訓練/測試時使用，不會放入特徵
    feat["__target__"] = (df[target_col] > 0).astype(int)
    feat["__return__"] = df[target_col]  # 保留原始報酬（用於回測）

    # 移除含 NaN 的列（warm-up 期）
    feat = feat.dropna()

    return feat


def train_test_split_temporal(
    feat_df: pd.DataFrame,
    train_ratio: float = 0.75,
) -> tuple:
    """
    時間序列的訓練/測試切分（嚴格按時間順序，絕不隨機）。

    train_ratio = 0.75 → 前75%為訓練集，後25%為測試集
    這樣可以確保測試集的日期都在訓練集之後，模擬真實投資場景。

    回傳：(X_train, X_test, y_train, y_test, return_test, split_date)
    """
    feature_cols = [c for c in feat_df.columns
                    if not c.startswith("__")]
    X = feat_df[feature_cols].values
    y = feat_df["__target__"].values
    ret = feat_df["__return__"].values

    split_idx = int(len(X) * train_ratio)
    split_date = feat_df.index[split_idx].strftime("%Y-%m-%d")

    return (
        X[:split_idx], X[split_idx:],
        y[:split_idx], y[split_idx:],
        ret[split_idx:],
        split_date,
        feat_df.index[split_idx:],
        feature_cols,
    )
