"""
model.py — Walk-Forward 機器學習模型（嚴格無資料洩漏）

架構：
  1. 特徵正規化：StandardScaler 只在訓練集 fit，測試集只做 transform
  2. Walk-Forward 驗證：TimeSeriesSplit，每折訓練集都在驗證集之前
  3. 最終預測：用全訓練集重新訓練，對測試集生成投資信號
  4. 回測：用投資信號的報酬 vs 買入持有基準比較

為何不能用 k-fold 交叉驗證？
  → 傳統 k-fold 會讓「未來資料」出現在訓練集，嚴重洩漏
  → Walk-Forward 確保每次訓練的時間都在驗證的時間之前
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    roc_auc_score, accuracy_score, f1_score,
    precision_score, recall_score, confusion_matrix,
)


# ─────────────────────────────────────────────
# 正規化（防洩漏版本）
# ─────────────────────────────────────────────

class LeakFreeScaler:
    """
    時間序列安全的正規化器。
    fit 只在訓練集執行，測試集使用訓練集的統計量做 transform。
    """
    def __init__(self):
        self.scaler = StandardScaler()
        self._fitted = False

    def fit_transform_train(self, X_train: np.ndarray) -> np.ndarray:
        """在訓練集上 fit 並 transform（此為唯一 fit 的地方）"""
        result = self.scaler.fit_transform(X_train)
        self._fitted = True
        return result

    def transform_test(self, X_test: np.ndarray) -> np.ndarray:
        """測試集只做 transform，使用訓練集的 mean/std → 無洩漏"""
        if not self._fitted:
            raise RuntimeError("請先呼叫 fit_transform_train()")
        return self.scaler.transform(X_test)

    def transform_latest(self, X_latest: np.ndarray) -> np.ndarray:
        """對最新資料做預測時使用"""
        return self.transform_test(X_latest)


# ─────────────────────────────────────────────
# Walk-Forward 驗證
# ─────────────────────────────────────────────

def walk_forward_validate(
    X_train: np.ndarray,
    y_train: np.ndarray,
    n_splits: int = 5,
) -> Dict[str, Any]:
    """
    在訓練集內部執行 Walk-Forward 驗證（不碰測試集）。

    TimeSeriesSplit 確保：
      fold 1: 訓練 [0:200]，驗證 [200:300]
      fold 2: 訓練 [0:300]，驗證 [300:400]
      ...每一折的驗證都在訓練之後

    回傳各折的 AUC-ROC 和準確率。
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)
    fold_scores = []

    for fold_idx, (tr_idx, val_idx) in enumerate(tscv.split(X_train)):
        # 每一折都重新 fit Scaler → 只用該折的訓練資料
        fold_scaler = StandardScaler()
        X_tr = fold_scaler.fit_transform(X_train[tr_idx])
        X_val = fold_scaler.transform(X_train[val_idx])  # 無洩漏

        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            min_samples_leaf=20,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_tr, y_train[tr_idx])

        y_prob = model.predict_proba(X_val)[:, 1]
        y_pred = (y_prob > 0.5).astype(int)

        auc = roc_auc_score(y_train[val_idx], y_prob) if len(np.unique(y_train[val_idx])) > 1 else 0.5
        acc = accuracy_score(y_train[val_idx], y_pred)

        fold_scores.append({
            "fold": fold_idx + 1,
            "auc_roc": round(float(auc), 4),
            "accuracy": round(float(acc), 4),
            "n_train": len(tr_idx),
            "n_val": len(val_idx),
        })

    mean_auc = np.mean([s["auc_roc"] for s in fold_scores])
    mean_acc = np.mean([s["accuracy"] for s in fold_scores])

    return {
        "folds": fold_scores,
        "mean_auc_roc": round(float(mean_auc), 4),
        "mean_accuracy": round(float(mean_acc), 4),
        "note": "Walk-Forward 驗證（每折訓練集都在驗證集之前，無資料洩漏）",
    }


# ─────────────────────────────────────────────
# 主模型訓練與預測
# ─────────────────────────────────────────────

def train_and_evaluate(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    ret_test: np.ndarray,
    test_dates: pd.DatetimeIndex,
    feature_names: List[str],
    n_wf_splits: int = 5,
) -> Dict[str, Any]:
    """
    完整訓練流程：
    1. Walk-Forward 驗證（只在訓練集內）
    2. 用全訓練集重新訓練最終模型
    3. 正規化測試集（使用訓練集 fit 的 Scaler → 無洩漏）
    4. 在測試集上評估 + 生成投資信號
    5. 回測（策略報酬 vs 買入持有）
    """
    # Step 1: Walk-Forward 驗證
    wf_result = walk_forward_validate(X_train, y_train, n_splits=n_wf_splits)

    # Step 2: 用全訓練集 fit Scaler + 訓練最終模型
    scaler = LeakFreeScaler()
    X_tr_scaled = scaler.fit_transform_train(X_train)  # 唯一的 fit

    final_model = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        min_samples_leaf=15,
        random_state=42,
        n_jobs=-1,
    )
    final_model.fit(X_tr_scaled, y_train)

    # Step 3: 測試集正規化（只做 transform → 無洩漏）
    X_te_scaled = scaler.transform_test(X_test)

    # Step 4: 測試集預測
    y_prob_test = final_model.predict_proba(X_te_scaled)[:, 1]
    y_pred_test = (y_prob_test > 0.5).astype(int)

    test_auc  = roc_auc_score(y_test, y_prob_test) if len(np.unique(y_test)) > 1 else 0.5
    test_acc  = accuracy_score(y_test, y_pred_test)
    test_f1   = f1_score(y_test, y_pred_test, zero_division=0)
    test_prec = precision_score(y_test, y_pred_test, zero_division=0)
    test_rec  = recall_score(y_test, y_pred_test, zero_division=0)

    # ── 混淆矩陣 (Confusion Matrix) ─────────────────────────────────────
    # 列 = 實際值，欄 = 預測值
    # [[TN, FP],    TN = 預測下跌且真的下跌（正確避開）
    #  [FN, TP]]    TP = 預測上漲且真的上漲（正確買入）
    #               FP = 預測上漲但實際下跌（誤買）
    #               FN = 預測下跌但實際上漲（誤放棄）
    cm = confusion_matrix(y_test, y_pred_test)
    tn, fp, fn, tp = cm.ravel() if cm.shape == (2, 2) else (0, 0, 0, 0)

    # Step 5: 回測
    backtest = _backtest(y_prob_test, ret_test, test_dates)

    # Step 6: 特徵重要性
    importance = _feature_importance(final_model, feature_names)

    # Step 7: 生成歷史信號序列（用於前端繪圖）
    signals = _build_signal_series(y_prob_test, ret_test, test_dates)

    return {
        "walk_forward": wf_result,
        "test_performance": {
            "auc_roc":   round(float(test_auc),  4),
            "accuracy":  round(float(test_acc),  4),
            "f1_score":  round(float(test_f1),   4),
            "precision": round(float(test_prec), 4),
            "recall":    round(float(test_rec),  4),
            "confusion_matrix": {
                "TP": int(tp), "TN": int(tn),
                "FP": int(fp), "FN": int(fn),
                "note": {
                    "TP": "預測上漲且實際上漲（正確買入）",
                    "TN": "預測下跌且實際下跌（正確避開）",
                    "FP": "預測上漲但實際下跌（誤買，損失）",
                    "FN": "預測下跌但實際上漲（誤放棄，錯過獲利）",
                },
            },
            "n_samples": len(y_test),
            "note": "測試集完全未參與訓練或 Scaler fit，確保無資料洩漏",
        },
        "backtest": backtest,
        "feature_importance": importance,
        "signals": signals,
        "model": final_model,
        "scaler": scaler,
    }


# ─────────────────────────────────────────────
# 回測
# ─────────────────────────────────────────────

def _backtest(
    proba: np.ndarray,
    actual_returns: np.ndarray,
    dates: pd.DatetimeIndex,
    buy_threshold: float = 0.55,
    sell_threshold: float = 0.45,
) -> Dict[str, Any]:
    """
    簡單回測：
    - 當模型預測上漲機率 > buy_threshold → 做多（持有）
    - 當機率 < sell_threshold → 空手（不持有）
    - 否則 → 維持前日部位

    比較：策略 vs 買入持有（Benchmark）
    """
    position = 0.0  # 0 = 空手, 1 = 持有
    strategy_returns = []
    positions_list = []

    for p, r in zip(proba, actual_returns):
        if p > buy_threshold:
            position = 1.0
        elif p < sell_threshold:
            position = 0.0
        # else: 維持前日部位

        strategy_returns.append(position * r)
        positions_list.append(position)

    strategy_returns = np.array(strategy_returns)
    benchmark_returns = actual_returns.copy()

    # 累積報酬
    strat_cum  = np.exp(np.cumsum(strategy_returns)) - 1
    bench_cum  = np.exp(np.cumsum(benchmark_returns)) - 1

    # Sharpe Ratio（年化）
    strat_sharpe  = _sharpe(strategy_returns)
    bench_sharpe  = _sharpe(benchmark_returns)

    # 最大回撤
    strat_dd  = _max_drawdown(strategy_returns)
    bench_dd  = _max_drawdown(benchmark_returns)

    # 勝率（做多時）
    long_mask = np.array(positions_list) == 1
    win_rate  = float(np.mean(actual_returns[long_mask] > 0)) if long_mask.any() else 0

    # 時間序列（前端用）
    ts = []
    for i, d in enumerate(dates):
        ts.append({
            "date": d.strftime("%Y-%m-%d"),
            "strategy_cum_return": round(float(strat_cum[i] * 100), 2),
            "benchmark_cum_return": round(float(bench_cum[i] * 100), 2),
            "position": int(positions_list[i]),
            "signal_prob": round(float(proba[i]), 4),
        })

    return {
        "strategy": {
            "total_return_pct": round(float(strat_cum[-1] * 100), 2),
            "sharpe_ratio": strat_sharpe,
            "max_drawdown_pct": round(float(strat_dd * 100), 2),
            "win_rate_pct": round(win_rate * 100, 2),
            "days_in_market_pct": round(float(long_mask.mean() * 100), 1),
        },
        "benchmark": {
            "total_return_pct": round(float(bench_cum[-1] * 100), 2),
            "sharpe_ratio": bench_sharpe,
            "max_drawdown_pct": round(float(bench_dd * 100), 2),
        },
        "alpha_pct": round(float((strat_cum[-1] - bench_cum[-1]) * 100), 2),
        "timeseries": ts,
        "params": {
            "buy_threshold": buy_threshold,
            "sell_threshold": sell_threshold,
        },
    }


def _sharpe(returns: np.ndarray, risk_free: float = 0.0, periods: int = 252) -> float:
    mu = np.mean(returns)
    sigma = np.std(returns)
    if sigma < 1e-9:
        return 0.0
    return round(float((mu - risk_free / periods) / sigma * np.sqrt(periods)), 3)


def _max_drawdown(returns: np.ndarray) -> float:
    cum = np.exp(np.cumsum(returns))
    running_max = np.maximum.accumulate(cum)
    drawdown = (cum - running_max) / running_max
    return float(np.min(drawdown))


def _feature_importance(model, feature_names: List[str], top_n: int = 15) -> List[Dict]:
    imp = model.feature_importances_
    pairs = sorted(zip(feature_names, imp), key=lambda x: x[1], reverse=True)
    return [
        {"feature": name, "importance": round(float(val), 6)}
        for name, val in pairs[:top_n]
    ]


def _build_signal_series(
    proba: np.ndarray,
    returns: np.ndarray,
    dates: pd.DatetimeIndex,
) -> List[Dict]:
    result = []
    for i, d in enumerate(dates):
        p = float(proba[i])
        if p > 0.60:
            signal = "BUY"
        elif p < 0.40:
            signal = "AVOID"
        else:
            signal = "HOLD"
        result.append({
            "date": d.strftime("%Y-%m-%d"),
            "probability_up": round(p, 4),
            "signal": signal,
            "actual_return_pct": round(float(returns[i]) * 100, 3),
        })
    return result


# ─────────────────────────────────────────────
# 最新預測（線上預測）
# ─────────────────────────────────────────────

def predict_current(
    model,
    scaler: LeakFreeScaler,
    latest_features: np.ndarray,
    feature_names: List[str],
) -> Dict[str, Any]:
    """
    對最新一筆資料做預測（模擬「今天」的投資建議）。
    latest_features shape: (1, n_features)
    """
    X_scaled = scaler.transform_latest(latest_features)
    prob_up = float(model.predict_proba(X_scaled)[0, 1])

    if prob_up > 0.60:
        recommendation = "BUY"
        confidence = "HIGH" if prob_up > 0.70 else "MEDIUM"
    elif prob_up < 0.40:
        recommendation = "AVOID"
        confidence = "HIGH" if prob_up < 0.30 else "MEDIUM"
    else:
        recommendation = "HOLD"
        confidence = "LOW"

    return {
        "probability_up": round(prob_up, 4),
        "probability_down": round(1 - prob_up, 4),
        "recommendation": recommendation,
        "confidence": confidence,
        "top_features": {
            name: round(float(val), 6)
            for name, val in zip(feature_names, latest_features[0])
        },
    }
