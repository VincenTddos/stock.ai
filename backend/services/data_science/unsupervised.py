"""
unsupervised.py — 非監督式學習模組

1. PCA 主成分分析 (Principal Component Analysis)
   - 降維：將高維特徵壓縮為低維，保留最大變異
   - 使用特徵值/特徵向量找出資料的主要方向
   - 防洩漏：PCA 的 fit 只在訓練集執行

2. K-Means 市場狀態分群 (Market Regime Clustering)
   - 非監督式：不需要標籤，讓模型自動發現市場結構
   - 常見結果：牛市 / 熊市 / 震盪市 三種狀態
   - 用於輔助投資決策：不同市場狀態採用不同策略
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans


# ─────────────────────────────────────────────
# PCA 主成分分析
# ─────────────────────────────────────────────

def run_pca(
    returns: pd.DataFrame,
    n_components: int = 3,
    train_ratio: float = 0.75,
) -> Dict[str, Any]:
    """
    對報酬率矩陣執行 PCA 降維分析。

    防洩漏：
      - StandardScaler.fit() 只在訓練集
      - PCA.fit() 只在訓練集
      - 測試集只做 transform

    特徵值 (Eigenvalues)：代表每個主成分解釋的變異量
    特徵向量 (Eigenvectors)：每個主成分的方向（各股票的權重）
    """
    data = returns.dropna()
    split = int(len(data) * train_ratio)

    X_train = data.iloc[:split].values
    X_test  = data.iloc[split:].values

    # ── 正規化（只 fit 訓練集）──────────────────
    scaler = StandardScaler()
    X_tr_scaled = scaler.fit_transform(X_train)   # fit + transform
    X_te_scaled = scaler.transform(X_test)         # 只 transform → 無洩漏

    # ── PCA（只 fit 訓練集）────────────────────
    n_comp = min(n_components, X_tr_scaled.shape[1])
    pca = PCA(n_components=n_comp, random_state=42)
    pca.fit(X_tr_scaled)   # 只 fit 訓練集

    # 特徵值（解釋變異量）
    explained = pca.explained_variance_ratio_
    eigenvalues = pca.explained_variance_

    # 特徵向量（各主成分對各股票的貢獻）
    components = pd.DataFrame(
        pca.components_,
        columns=data.columns,
        index=[f"PC{i+1}" for i in range(n_comp)],
    )

    # 在訓練集和測試集上的主成分得分
    train_scores = pca.transform(X_tr_scaled)
    test_scores  = pca.transform(X_te_scaled)

    # 重建誤差（用於異常偵測）
    X_reconstructed = pca.inverse_transform(test_scores)
    reconstruction_error = np.mean((X_te_scaled - X_reconstructed) ** 2, axis=1)

    # 主成分時間序列（前端繪圖用）
    all_dates = data.index
    all_X = np.vstack([X_tr_scaled, X_te_scaled])
    all_scores = pca.transform(all_X)

    timeseries = []
    for i, date in enumerate(all_dates):
        row = {"date": date.strftime("%Y-%m-%d")}
        for j in range(n_comp):
            row[f"PC{j+1}"] = round(float(all_scores[i, j]), 4)
        timeseries.append(row)

    return {
        "n_components": n_comp,
        "explained_variance_ratio": [round(float(v), 4) for v in explained],
        "cumulative_explained": [
            round(float(v), 4) for v in np.cumsum(explained)
        ],
        "eigenvalues": [round(float(v), 4) for v in eigenvalues],
        "eigenvectors": components.round(4).to_dict(),
        "interpretation": {
            f"PC{i+1}": _interpret_pc(components.iloc[i])
            for i in range(n_comp)
        },
        "timeseries": timeseries,
        "anti_leakage": "Scaler 和 PCA 均只在訓練集 fit，測試集只做 transform",
    }


def _interpret_pc(component: pd.Series) -> str:
    """根據特徵向量的最大貢獻解讀主成分意義"""
    top = component.abs().nlargest(3)
    top_names = ", ".join(
        f"{name}({'+' if component[name] > 0 else '-'}{abs(component[name]):.2f})"
        for name in top.index
    )
    return f"主要由 {top_names} 驅動"


# ─────────────────────────────────────────────
# K-Means 市場狀態分群
# ─────────────────────────────────────────────

def run_market_regime(
    returns: pd.DataFrame,
    n_regimes: int = 3,
    window: int = 20,
    train_ratio: float = 0.75,
) -> Dict[str, Any]:
    """
    非監督式學習：K-Means 市場狀態分群

    特徵（使用滾動窗口，所有特徵 shift(1) → 無洩漏）：
      - 滾動平均報酬（趨勢）
      - 滾動波動率（風險）
      - 跨資產相關性（市場連動）

    分群結果通常對應：
      - 牛市 (Bull)：高報酬、低波動
      - 熊市 (Bear)：負報酬、高波動
      - 震盪 (Sideways)：低報酬、中波動

    防洩漏：K-Means 的 fit 只在訓練集，測試集只 predict
    """
    # 計算市場特徵（所有都 shift(1) 避免洩漏）
    feat = pd.DataFrame(index=returns.index)

    for col in returns.columns:
        shifted = returns[col].shift(1)
        feat[f"{col}_mean{window}d"]  = shifted.rolling(window).mean()
        feat[f"{col}_vol{window}d"]   = shifted.rolling(window).std()
        feat[f"{col}_trend"]          = shifted.rolling(5).mean() - shifted.rolling(20).mean()

    feat = feat.dropna()

    split = int(len(feat) * train_ratio)
    X_train = feat.iloc[:split].values
    X_test  = feat.iloc[split:].values

    # 正規化（只 fit 訓練集）
    scaler = StandardScaler()
    X_tr_scaled = scaler.fit_transform(X_train)
    X_te_scaled = scaler.transform(X_test)       # 無洩漏

    # K-Means 分群（只 fit 訓練集）
    km = KMeans(n_clusters=n_regimes, random_state=42, n_init=10)
    km.fit(X_tr_scaled)   # 只 fit 訓練集

    # 預測所有資料的市場狀態
    all_X = np.vstack([X_tr_scaled, X_te_scaled])
    all_labels = km.predict(all_X)

    # 根據群心特徵命名市場狀態
    centers_df = pd.DataFrame(
        scaler.inverse_transform(km.cluster_centers_),
        columns=feat.columns,
    )
    regime_names = _name_regimes(centers_df, returns.columns.tolist())

    # 時間序列（前端繪圖用）
    timeseries = []
    for i, date in enumerate(feat.index):
        label = int(all_labels[i])
        timeseries.append({
            "date": date.strftime("%Y-%m-%d"),
            "regime_id": label,
            "regime_name": regime_names[label],
            "is_train": i < split,
        })

    # 各市場狀態統計
    regime_stats = {}
    for regime_id, name in regime_names.items():
        mask = all_labels == regime_id
        regime_returns = returns.iloc[
            returns.index.isin(feat.index[mask])
        ].values.flatten()
        regime_stats[name] = {
            "regime_id": regime_id,
            "n_days": int(mask.sum()),
            "pct_of_time": round(float(mask.mean()) * 100, 1),
            "avg_daily_return": round(float(np.nanmean(regime_returns)), 6),
            "volatility": round(float(np.nanstd(regime_returns)), 6),
        }

    return {
        "n_regimes": n_regimes,
        "regime_names": regime_names,
        "regime_stats": regime_stats,
        "timeseries": timeseries,
        "current_regime": timeseries[-1] if timeseries else None,
        "anti_leakage": "KMeans fit 只在訓練集，測試集用 predict（非 fit_predict）",
    }


def _name_regimes(centers: pd.DataFrame, return_cols: List[str]) -> Dict[int, str]:
    """根據群心的平均報酬和波動率，自動命名市場狀態"""
    mean_cols = [c for c in centers.columns if "mean" in c and any(r in c for r in return_cols)]
    vol_cols  = [c for c in centers.columns if "vol"  in c and any(r in c for r in return_cols)]

    names = {}
    for i, row in centers.iterrows():
        avg_ret = row[mean_cols].mean() if mean_cols else 0
        avg_vol = row[vol_cols].mean() if vol_cols else 0

        if avg_ret > 0.0002 and avg_vol < centers[vol_cols].values.mean():
            names[i] = "牛市 (Bull)"
        elif avg_ret < -0.0002 or avg_vol > centers[vol_cols].values.mean() * 1.2:
            names[i] = "熊市 (Bear)"
        else:
            names[i] = "震盪 (Sideways)"

    # 確保名稱不重複
    seen = {}
    for k, v in names.items():
        if v in seen.values():
            names[k] = f"{v} II"
        seen[k] = names[k]

    return names
