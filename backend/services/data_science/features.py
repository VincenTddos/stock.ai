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
from typing import List, Dict, Any

try:
    from statsmodels.tsa.stattools import adfuller
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False


# ─────────────────────────────────────────────────────────────
# 時間序列定態性檢定 (Stationarity Test)
# ─────────────────────────────────────────────────────────────

def test_stationarity(returns: pd.DataFrame) -> Dict[str, Any]:
    """
    ADF 檢定（Augmented Dickey-Fuller Test）

    H0：序列具有單根（Non-stationary，非定態）
    H1：序列為定態（Stationary）

    p-value < 0.05 → 拒絕 H0 → 定態 ✅
    p-value > 0.05 → 無法拒絕 H0 → 非定態 ❌（需要差分）

    股票「價格」通常是非定態 → 需轉換為「報酬率」才能建模
    對數報酬率通常已是定態，這裡驗證此假設。
    """
    if not HAS_STATSMODELS:
        return {"error": "statsmodels 未安裝"}

    results = {}
    for col in returns.columns:
        series = returns[col].dropna()
        if len(series) < 20:
            continue
        try:
            adf_stat, p_val, usedlag, nobs, crit, _ = adfuller(series, autolag="AIC")
            results[col] = {
                "adf_statistic": round(float(adf_stat), 4),
                "p_value": round(float(p_val), 4),
                "is_stationary": bool(p_val < 0.05),
                "critical_values": {k: round(v, 3) for k, v in crit.items()},
                "verdict": (
                    "定態 (Stationary) - 可直接建模"
                    if p_val < 0.05 else
                    "非定態 (Non-stationary) - 建議差分或取對數報酬"
                ),
            }
        except Exception as e:
            results[col] = {"error": str(e)}
    return results


# ─────────────────────────────────────────────────────────────
# 技術指標 (Technical Indicators)
# ─────────────────────────────────────────────────────────────

def _rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """計算相對強弱指標（RSI）"""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    return 100 - (100 / (1 + rs))


def _macd(series: pd.Series,
          fast: int = 12, slow: int = 26, signal: int = 9
          ) -> tuple:
    """
    MACD 指標（Moving Average Convergence Divergence）
    - MACD 線   = EMA(12) - EMA(26)
    - 信號線    = EMA(MACD, 9)
    - 柱狀圖    = MACD 線 - 信號線 → 正值代表多頭動能增強

    防洩漏：傳入的 series 必須已 shift(1)
    """
    ema_fast   = series.ewm(span=fast,   adjust=False).mean()
    ema_slow   = series.ewm(span=slow,   adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram  = macd_line - signal_line
    return macd_line, signal_line, histogram


def _stochastic_kd(series: pd.Series,
                   k_period: int = 14, d_period: int = 3
                   ) -> tuple:
    """
    KD 線（Stochastic Oscillator）
    K 值 = (今日收盤 - N日最低) / (N日最高 - N日最低) × 100
    D 值 = K 值的 M 日移動平均

    K > 80 → 超買（可能回檔）
    K < 20 → 超賣（可能反彈）

    防洩漏：傳入的 series 必須已 shift(1)
    """
    lowest  = series.rolling(k_period).min()
    highest = series.rolling(k_period).max()
    k = (series - lowest) / (highest - lowest + 1e-9) * 100
    d = k.rolling(d_period).mean()
    return k, d


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

        # --- RSI 相對強弱指標 (基於昨天以前的收盤報酬) ---
        shifted = df[col].shift(1)
        rsi_vals = _rsi(shifted)
        feat[f"{col}_rsi14"] = rsi_vals
        # RSI 超買/超賣旗標
        feat[f"{col}_rsi_overbought"] = (rsi_vals > 70).astype(float)
        feat[f"{col}_rsi_oversold"]   = (rsi_vals < 30).astype(float)

        # --- MACD 指標 ---
        macd_line, signal_line, histogram = _macd(shifted)
        feat[f"{col}_macd"]        = macd_line
        feat[f"{col}_macd_signal"] = signal_line
        feat[f"{col}_macd_hist"]   = histogram
        # MACD 黃金/死亡交叉旗標
        feat[f"{col}_macd_cross_up"]   = ((macd_line > signal_line) &
                                          (macd_line.shift(1) <= signal_line.shift(1))).astype(float)
        feat[f"{col}_macd_cross_down"] = ((macd_line < signal_line) &
                                          (macd_line.shift(1) >= signal_line.shift(1))).astype(float)

        # --- KD 隨機指標 ---
        k_val, d_val = _stochastic_kd(shifted)
        feat[f"{col}_k"]         = k_val
        feat[f"{col}_d"]         = d_val
        feat[f"{col}_kd_diff"]   = k_val - d_val  # K 在 D 上方 → 多頭
        feat[f"{col}_kd_cross_up"]   = ((k_val > d_val) &
                                        (k_val.shift(1) <= d_val.shift(1))).astype(float)
        feat[f"{col}_kd_cross_down"] = ((k_val < d_val) &
                                        (k_val.shift(1) >= d_val.shift(1))).astype(float)

        # --- 短期 vs 長期均線比值 (Momentum 動量) ---
        ma5  = shifted.rolling(5).mean()
        ma20 = shifted.rolling(20).mean()
        ma60 = shifted.rolling(60).mean()
        feat[f"{col}_ma5_20_ratio"]  = ma5  / (ma20 + 1e-9)
        feat[f"{col}_ma20_60_ratio"] = ma20 / (ma60 + 1e-9)
        # 均線多頭排列旗標（5日 > 20日 > 60日）
        feat[f"{col}_bull_alignment"] = ((ma5 > ma20) & (ma20 > ma60)).astype(float)

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
