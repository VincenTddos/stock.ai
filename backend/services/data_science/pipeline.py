"""
pipeline.py — 整合入口，串接所有資料科學模組

提供兩個主要函式：
  run_correlation_analysis() → 台美股相關性分析
  run_signal_pipeline()      → 投資信號生成（Walk-Forward ML）
"""
from typing import List, Dict, Any
import numpy as np

from .fetcher import align_tw_us, remove_outliers_iqr
from .correlation import run_full_correlation
from .features import build_features, train_test_split_temporal
from .model import train_and_evaluate, predict_current
from .unsupervised import run_pca, run_market_regime


# ─────────────────────────────────────────────
# Pipeline 1: 相關性分析
# ─────────────────────────────────────────────

def run_correlation_analysis(
    tw_tickers: List[str],
    us_tickers: List[str],
    period: str = "3y",
    rolling_window: int = 30,
) -> Dict[str, Any]:
    """
    台美股相關性完整分析：
      - 靜態相關矩陣
      - 滾動相關係數（時變）
      - Granger 因果檢定
      - 落後期分析（找最佳領先天數）
    """
    # 1. 抓資料
    data = align_tw_us(tw_tickers, us_tickers, period)
    returns = data["returns"]
    tw_cols = data["tw_cols"]
    us_cols = data["us_cols"]

    if not tw_cols:
        raise ValueError(f"無法取得台股資料：{tw_tickers}")
    if not us_cols:
        raise ValueError(f"無法取得美股資料：{us_tickers}")

    # 2. 執行相關性分析
    result = run_full_correlation(returns, tw_cols, us_cols, rolling_window)
    result["tw_tickers"] = tw_cols
    result["us_tickers"] = us_cols
    result["period"] = period

    # 非監督式：PCA 降維 + 市場狀態分群
    try:
        result["pca"] = run_pca(returns[tw_cols + us_cols])
        result["market_regimes"] = run_market_regime(returns[tw_cols + us_cols])
    except Exception as e:
        result["pca"] = {"error": str(e)}
        result["market_regimes"] = {"error": str(e)}

    return result


# ─────────────────────────────────────────────
# Pipeline 2: 投資信號生成
# ─────────────────────────────────────────────

def run_signal_pipeline(
    target_ticker: str,
    feature_tickers: List[str],
    period: str = "4y",
    train_ratio: float = 0.75,
    n_wf_splits: int = 5,
) -> Dict[str, Any]:
    """
    Walk-Forward ML 投資信號流程：

    1. 抓取所有股票資料
    2. 計算對數報酬率
    3. 建立特徵矩陣（所有特徵嚴格使用昨天以前的資料）
    4. 時間序列切分（前75% 訓練，後25% 測試）
    5. Walk-Forward 驗證（在訓練集內部）
    6. 用全訓練集訓練最終模型（Scaler 只 fit 訓練集）
    7. 在測試集評估 + 回測
    8. 預測最新一天的投資建議

    防洩漏措施：
      ✅ 特徵全部 shift(1)
      ✅ 正規化 Scaler 只 fit 訓練集
      ✅ 時間序列切分（不隨機）
      ✅ Walk-Forward 交叉驗證
    """
    all_tickers = list(dict.fromkeys([target_ticker] + feature_tickers))
    data = align_tw_us(
        tw_tickers=[t for t in all_tickers if ".TW" in t or "^TW" in t],
        us_tickers=[t for t in all_tickers if ".TW" not in t and "^TW" not in t],
        period=period,
    )
    returns = data["returns"]

    if target_ticker not in returns.columns:
        raise ValueError(f"無法取得目標股票資料：{target_ticker}")

    # 異常值處理（IQR 截斷，只在全資料集計算邊界）
    # 注意：在 train_test_split 後理論上只用訓練集，
    # 但 IQR k=5 非常寬鬆，主要排除明顯的資料錯誤
    returns, _outlier_bounds = remove_outliers_iqr(returns, k=5.0)

    available_features = [t for t in feature_tickers if t in returns.columns]
    if not available_features:
        raise ValueError(f"無法取得任何特徵股票資料：{feature_tickers}")

    # 3. 建立特徵矩陣
    feat_df = build_features(
        returns=returns,
        target_col=target_ticker,
        feature_cols=available_features,
    )

    if len(feat_df) < 200:
        raise ValueError(
            f"資料點不足（只有 {len(feat_df)} 天），請增加 period 至少 3y。"
        )

    # 4. 時間序列切分
    (X_train, X_test, y_train, y_test,
     ret_test, split_date, test_dates, feature_names) = train_test_split_temporal(
        feat_df, train_ratio
    )

    # 5-8. 訓練、驗證、回測
    result = train_and_evaluate(
        X_train, X_test, y_train, y_test,
        ret_test, test_dates, feature_names,
        n_wf_splits=n_wf_splits,
    )

    # 最新一天的預測
    latest_X = X_test[-1:] if len(X_test) > 0 else X_train[-1:]
    current = predict_current(
        result["model"],
        result["scaler"],
        latest_X,
        feature_names,
    )

    # 整理輸出（移除 model/scaler 物件，不可 JSON 序列化）
    result.pop("model", None)
    result.pop("scaler", None)

    result["current_signal"] = current
    result["meta"] = {
        "target": target_ticker,
        "feature_tickers": available_features,
        "period": period,
        "total_samples": len(feat_df),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "train_end_date": split_date,
        "test_start_date": split_date,
        "anti_leakage_measures": [
            "所有特徵使用 .shift(1)，只含昨天以前的資訊",
            "StandardScaler 只在訓練集 fit，測試集只做 transform",
            "時間序列切分（前75%訓練，後25%測試，不隨機）",
            f"Walk-Forward 驗證（{n_wf_splits} 折，每折訓練集都在驗證集之前）",
        ],
    }

    return result
