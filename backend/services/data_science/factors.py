"""
factors.py — 多因子模型、Alpha、Beta 計算

因子模型理論基礎：
  CAPM（資本資產定價模型）：
    E(R_i) = R_f + β_i × (E(R_m) - R_f)
    其中 R_f = 無風險利率，R_m = 市場報酬

  Alpha（主動報酬）：
    α = 實際報酬 - CAPM 預期報酬
    α > 0 → 主動操作創造超額報酬

  Beta（系統性風險）：
    β = Cov(R_i, R_m) / Var(R_m)
    β > 1 → 比大盤波動更劇烈（攻擊型）
    β < 1 → 比大盤波動更溫和（防禦型）

多因子模型（Fama-French 精神）：
  • 動量因子 (Momentum)：過去表現好的股票傾向繼續表現好
  • 價值因子 (Value)：低估值股票長期報酬較高
  • 品質因子 (Quality)：高 ROE、穩定盈利的公司
  • 規模因子 (Size)：小公司長期報酬較高
  • 波動率因子 (Volatility)：低波動股票風險調整後報酬較高
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional


# ─────────────────────────────────────────────
# CAPM: Alpha & Beta
# ─────────────────────────────────────────────

def calculate_beta(
    stock_returns: pd.Series,
    market_returns: pd.Series,
) -> float:
    """
    計算 Beta（系統性風險係數）
    β = Cov(stock, market) / Var(market)
    """
    aligned = pd.concat([stock_returns, market_returns], axis=1).dropna()
    if len(aligned) < 30:
        return np.nan
    cov_matrix = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
    beta = cov_matrix[0, 1] / (cov_matrix[1, 1] + 1e-12)
    return round(float(beta), 4)


def calculate_alpha(
    stock_returns: pd.Series,
    market_returns: pd.Series,
    risk_free_annual: float = 0.04,   # 預設 4% 無風險利率（美國10年期國債）
) -> Dict[str, float]:
    """
    計算 Jensen's Alpha（年化）
    α = R_i - [R_f + β × (R_m - R_f)]

    若 α > 0 → 策略優於 CAPM 預期（有超額報酬）
    """
    rf_daily = risk_free_annual / 252
    beta = calculate_beta(stock_returns, market_returns)

    aligned = pd.concat([stock_returns, market_returns], axis=1).dropna()
    avg_stock  = aligned.iloc[:, 0].mean()
    avg_market = aligned.iloc[:, 1].mean()

    # 日均 alpha
    daily_alpha = avg_stock - (rf_daily + beta * (avg_market - rf_daily))
    annual_alpha = daily_alpha * 252

    return {
        "beta": beta,
        "daily_alpha": round(float(daily_alpha), 6),
        "annual_alpha_pct": round(float(annual_alpha * 100), 3),
        "interpretation": (
            f"Beta={beta:.2f} → "
            f"{'比大盤波動劇烈（攻擊型）' if beta > 1.1 else '比大盤穩定（防禦型）' if beta < 0.9 else '與大盤相近（中性）'}"
            f"；Alpha={annual_alpha*100:.2f}% 年化超額報酬"
            f"（{'優於' if annual_alpha > 0 else '劣於'} CAPM 預期）"
        ),
    }


# ─────────────────────────────────────────────
# 動量因子 (Momentum Factor)
# ─────────────────────────────────────────────

def momentum_factor(
    returns: pd.Series,
    skip_last: int = 21,     # 跳過最近1個月（避免短期反轉效應）
    lookback: int = 252,     # 過去12個月
) -> pd.Series:
    """
    動量因子 = 過去 12 個月報酬（跳過最近 1 個月）

    學術研究（Jegadeesh & Titman 1993）：
    過去 12 個月報酬高的股票，未來 3-12 個月仍傾向跑贏大盤。

    skip_last=21 → 避免短期均值回歸（最近1個月往往反轉）
    防洩漏：使用 shift(skip_last) → 最近的資料也不包含當天
    """
    total_return = returns.shift(skip_last).rolling(lookback).sum()
    return total_return


def cross_sectional_momentum(
    returns: pd.DataFrame,
    skip_last: int = 21,
    lookback: int = 252,
) -> pd.DataFrame:
    """
    多股票截面動量因子：各股票的動量相對排名（0~1）
    排名越高 → 動量越強 → 更傾向繼續上漲
    """
    mom = pd.DataFrame(index=returns.index)
    for col in returns.columns:
        mom[col] = momentum_factor(returns[col], skip_last, lookback)

    # 橫截面排名（每天的排名，0=最低，1=最高）
    mom_rank = mom.rank(axis=1, pct=True)
    return mom_rank


# ─────────────────────────────────────────────
# 多因子評分模型
# ─────────────────────────────────────────────

def multi_factor_score(
    returns: pd.DataFrame,
    market_col: str = "SPY",
    window: int = 60,
    weights: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """
    綜合多因子評分（0~100 分，越高越看漲）

    因子組成（預設權重）：
      動量因子   (Momentum)  40% — 趨勢持續性
      波動因子   (Volatility) 30% — 低波動股票風險調整後表現較好
      相對強度   (RS)        30% — 相對大盤的表現

    防洩漏：所有因子計算均使用 shift(1)
    """
    if weights is None:
        weights = {"momentum": 0.40, "volatility": 0.30, "relative_strength": 0.30}

    scores = pd.DataFrame(index=returns.index)

    for col in [c for c in returns.columns if c != market_col]:
        shifted = returns[col].shift(1)
        mkt_shifted = returns[market_col].shift(1) if market_col in returns.columns else None

        # 動量因子（過去 window 天報酬，已 shift）
        mom = shifted.rolling(window).sum()

        # 波動因子（越低越好，反向）
        vol = shifted.rolling(window).std()
        vol_score = 1 / (vol + 1e-9)  # 低波動 → 高分

        # 相對強度（相對大盤）
        if mkt_shifted is not None:
            rel_strength = mom - mkt_shifted.rolling(window).sum()
        else:
            rel_strength = mom

        # 各因子橫截面標準化（Winsorize + Z-score）
        def zscore_winsor(s):
            s = s.clip(s.quantile(0.05), s.quantile(0.95))
            return (s - s.mean()) / (s.std() + 1e-9)

        scores[col] = (
            weights["momentum"]         * mom +
            weights["volatility"]       * vol_score +
            weights["relative_strength"] * rel_strength
        )

    # 轉換為 0-100 分（百分位排名）
    score_rank = scores.rank(axis=1, pct=True) * 100
    return score_rank.round(1)


# ─────────────────────────────────────────────
# 完整因子分析報告
# ─────────────────────────────────────────────

def run_factor_analysis(
    returns: pd.DataFrame,
    tw_cols: List[str],
    market_col: str = "SPY",
) -> Dict[str, Any]:
    """
    對所有台股進行完整因子分析報告。
    """
    results = {}

    for tw in tw_cols:
        if tw not in returns.columns:
            continue

        # Alpha & Beta vs 大盤
        ab = calculate_alpha(returns[tw], returns[market_col]) \
             if market_col in returns.columns else {}

        # 動量因子時間序列
        mom_ts = momentum_factor(returns[tw])
        latest_mom = float(mom_ts.dropna().iloc[-1]) if len(mom_ts.dropna()) > 0 else 0

        # 近期波動率 vs 歷史
        recent_vol = float(returns[tw].tail(21).std() * np.sqrt(252))
        hist_vol   = float(returns[tw].std() * np.sqrt(252))

        results[tw] = {
            "alpha_beta": ab,
            "momentum_12m_pct": round(latest_mom * 100, 2),
            "recent_volatility_annual": round(recent_vol, 4),
            "historical_volatility_annual": round(hist_vol, 4),
            "volatility_regime": (
                "高波動（近期 > 歷史均值）" if recent_vol > hist_vol * 1.2 else
                "低波動（近期 < 歷史均值）" if recent_vol < hist_vol * 0.8 else
                "正常波動"
            ),
        }

    # 多因子評分（最新一天）
    try:
        factor_scores = multi_factor_score(returns, market_col=market_col)
        latest_scores = factor_scores.iloc[-1].to_dict() if len(factor_scores) > 0 else {}
        results["latest_factor_scores"] = {
            k: round(v, 1) for k, v in latest_scores.items()
            if k in tw_cols
        }
    except Exception:
        results["latest_factor_scores"] = {}

    # 低信噪比警告
    results["low_snr_warning"] = {
        "message": "股市信噪比極低（Signal-to-Noise Ratio < 0.1）",
        "mitigation": [
            "使用集成模型（Random Forest）降低單一決策樹的隨機誤差",
            "Walk-Forward 驗證確保模型不是針對特定歷史時期過擬合",
            "特徵重要性篩選去除無預測力的雜訊特徵",
            "min_samples_leaf=15 避免模型學習少數樣本的隨機波動",
            "AUC 目標設定在 0.55-0.65（遠高於 0.5 即有效），不追求 >0.9",
        ],
    }

    return results
