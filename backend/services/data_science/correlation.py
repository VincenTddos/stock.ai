"""
correlation.py — 台美股市相關性分析

分析項目：
  1. 靜態相關係數矩陣（Pearson Correlation）
  2. 滾動相關係數（Rolling Correlation，時變相關性）
  3. Granger 因果檢定（US 是否 Granger-cause TW？）
  4. 落後期分析（Cross-Correlation Function，找最佳領先落後天數）
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any

try:
    from statsmodels.tsa.stattools import grangercausalitytests, ccf
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False


def correlation_matrix(returns: pd.DataFrame) -> Dict[str, Any]:
    """
    計算靜態 Pearson 相關係數矩陣。
    回傳適合前端繪製熱力圖的格式。
    """
    corr = returns.corr()

    # 轉成前端友善的格式：[{x, y, value}] 列表
    cells = []
    for i, row in enumerate(corr.index):
        for j, col in enumerate(corr.columns):
            cells.append({
                "x": col,
                "y": row,
                "value": round(float(corr.loc[row, col]), 4),
            })

    return {
        "tickers": list(corr.columns),
        "matrix": corr.round(4).to_dict(),
        "cells": cells,  # 用於熱力圖
    }


def rolling_correlation(
    returns: pd.DataFrame,
    col_a: str,
    col_b: str,
    window: int = 30,
) -> List[Dict]:
    """
    計算兩支股票間的滾動相關係數（時變相關）。
    window = 30 → 每個資料點使用前30個交易日計算。
    """
    if col_a not in returns.columns or col_b not in returns.columns:
        return []

    roll = returns[col_a].rolling(window).corr(returns[col_b])
    roll = roll.dropna()

    result = []
    for date, val in roll.items():
        if not np.isnan(val):
            result.append({
                "date": date.strftime("%Y-%m-%d"),
                "correlation": round(float(val), 4),
            })
    return result


def granger_causality(
    returns: pd.DataFrame,
    cause_col: str,
    effect_col: str,
    max_lag: int = 5,
) -> Dict[str, Any]:
    """
    Granger 因果檢定：
    H0：cause_col 不能幫助預測 effect_col（cause 不 Granger-cause effect）
    若 p-value < 0.05 → 拒絕 H0 → cause 在統計上 Granger-cause effect

    注意：Granger 因果 ≠ 真實因果關係，只代表「領先預測能力」。
    """
    if not HAS_STATSMODELS:
        return {"error": "statsmodels 未安裝，無法執行 Granger 檢定。"}

    if cause_col not in returns.columns or effect_col not in returns.columns:
        return {"error": f"找不到欄位：{cause_col} 或 {effect_col}"}

    data = returns[[effect_col, cause_col]].dropna()
    if len(data) < max_lag * 10:
        return {"error": "資料量不足，請增加 period。"}

    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw = grangercausalitytests(data, maxlag=max_lag, verbose=False)
        results = {}
        for lag, res in raw.items():
            # 取 F 檢定的 p-value
            pval = res[0]["ssr_ftest"][1]
            results[f"lag_{lag}d"] = {
                "p_value": round(float(pval), 4),
                "significant": bool(pval < 0.05),
                "interpretation": (
                    f"{cause_col} 能顯著預測 {effect_col}（{lag}天後）"
                    if pval < 0.05 else
                    f"{cause_col} 對 {effect_col} 無顯著預測力（{lag}天後）"
                ),
            }
        best_lag = min(results, key=lambda k: results[k]["p_value"])
        return {
            "cause": cause_col,
            "effect": effect_col,
            "by_lag": results,
            "best_lag": best_lag,
            "conclusion": (
                f"[{'YES' if results[best_lag]['significant'] else 'NO'}] "
                f"{cause_col} {'存在' if results[best_lag]['significant'] else '不存在'}"
                f"對 {effect_col} 的 Granger 因果關係"
                f"（最佳落後期：{best_lag}，p={results[best_lag]['p_value']}）"
            ),
        }
    except Exception as e:
        return {"error": str(e)}


def lag_cross_correlation(
    returns: pd.DataFrame,
    col_a: str,
    col_b: str,
    max_lag: int = 10,
) -> List[Dict]:
    """
    計算交叉相關函數（CCF）：
    找出 col_a 領先/落後 col_b 多少天時相關性最強。
    負 lag → col_a 領先 col_b
    正 lag → col_a 落後 col_b
    """
    if col_a not in returns.columns or col_b not in returns.columns:
        return []

    s_a = returns[col_a].dropna()
    s_b = returns[col_b].dropna()
    aligned = pd.concat([s_a, s_b], axis=1).dropna()

    result = []
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            corr = aligned.iloc[:lag, 0].corr(aligned.iloc[-lag:, 1])
        elif lag > 0:
            corr = aligned.iloc[lag:, 0].corr(aligned.iloc[:-lag, 1])
        else:
            corr = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])

        result.append({
            "lag": lag,
            "correlation": round(float(corr) if not np.isnan(corr) else 0, 4),
            "label": (
                f"{col_a} 領先 {abs(lag)} 天" if lag < 0 else
                f"{col_a} 落後 {lag} 天" if lag > 0 else "同步"
            ),
        })
    return result


def run_full_correlation(
    returns: pd.DataFrame,
    tw_cols: List[str],
    us_cols: List[str],
    rolling_window: int = 30,
) -> Dict[str, Any]:
    """
    完整相關性分析流程，回傳前端所需的所有資料。
    """
    all_cols = tw_cols + us_cols

    # 1. 靜態相關矩陣
    corr_result = correlation_matrix(returns[all_cols])

    # 2. 滾動相關（取第一對 TW-US 組合）
    rolling_pairs = []
    for tw in tw_cols[:2]:
        for us in us_cols[:2]:
            roll_data = rolling_correlation(returns, tw, us, rolling_window)
            if roll_data:
                rolling_pairs.append({
                    "pair": f"{tw} vs {us}",
                    "data": roll_data,
                })

    # 3. Granger 因果（US → TW 方向）
    granger_results = []
    for us in us_cols[:3]:
        for tw in tw_cols[:2]:
            g = granger_causality(returns, cause_col=us, effect_col=tw)
            granger_results.append(g)

    # 4. 落後期分析（第一組 TW-US 對）
    lag_results = []
    if tw_cols and us_cols:
        lag_results = lag_cross_correlation(returns, us_cols[0], tw_cols[0])

    # 5. 基本統計摘要
    stats = {}
    for col in all_cols:
        s = returns[col].dropna()
        stats[col] = {
            "mean_daily_return": round(float(s.mean()), 6),
            "annualized_return": round(float(s.mean() * 252), 4),
            "annualized_volatility": round(float(s.std() * np.sqrt(252)), 4),
            "sharpe_approx": round(
                float(s.mean() / (s.std() + 1e-9) * np.sqrt(252)), 3
            ),
            "skewness": round(float(s.skew()), 3),
            "kurtosis": round(float(s.kurtosis()), 3),
        }

    return {
        "correlation_matrix": corr_result,
        "rolling_correlations": rolling_pairs,
        "granger_causality": granger_results,
        "lag_analysis": lag_results,
        "stats": stats,
        "period_days": len(returns),
    }
