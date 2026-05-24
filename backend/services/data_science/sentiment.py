"""
sentiment.py — 新聞情緒分析 (Sentiment Analysis)

流程：
  1. 用 yfinance 抓取最新新聞標題（免費，無需額外 API key）
  2. 用 Gemini AI 將新聞情緒量化為數值（-1 到 +1）
  3. 計算整體情緒分數、分布，作為投資決策的輔助特徵

情緒量化方式：
  +1.0  = 極度正面（大幅超越預期、突破性創新）
  +0.5  = 正面（業績成長、市場擴張）
   0.0  = 中性（一般公告、產品更新）
  -0.5  = 負面（業績下滑、競爭壓力）
  -1.0  = 極度負面（醜聞、重大損失、監管處罰）

注意事項（防洩漏）：
  情緒分析只能用於「當下」的決策，不能回溯放入訓練集
  → 如要作為 ML 特徵，需確保新聞日期在交易日「開盤前」
"""
import os
import yfinance as yf
import google.generativeai as genai
from typing import Dict, Any, List, Optional
import json
import time


def fetch_news(ticker: str, max_items: int = 10) -> List[Dict]:
    """
    從 Yahoo Finance 抓取最新新聞。
    回傳：[{title, publisher, link, publish_time}, ...]
    """
    try:
        stock = yf.Ticker(ticker)
        news_raw = stock.news or []
        result = []
        for item in news_raw[:max_items]:
            content = item.get("content", {})
            title = content.get("title", "") or item.get("title", "")
            publisher = (
                content.get("provider", {}).get("displayName", "") or
                item.get("publisher", "")
            )
            if title:
                result.append({
                    "title": title,
                    "publisher": publisher,
                })
        return result
    except Exception as e:
        return [{"title": f"無法取得新聞：{e}", "publisher": ""}]


def score_sentiment_with_ai(
    ticker: str,
    company_name: str,
    news_items: List[Dict],
) -> Dict[str, Any]:
    """
    用 Gemini AI 對新聞標題進行情緒分析。

    回傳結構化情緒評分，避免主觀偏差。
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY 未設定"}

    if not news_items:
        return {"error": "無新聞資料"}

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    )

    headlines = "\n".join(
        f"{i+1}. [{item['publisher']}] {item['title']}"
        for i, item in enumerate(news_items)
    )

    prompt = f"""你是一位專業的財務情緒分析師。
請分析以下關於 {company_name}（{ticker}）的新聞標題，評估其對股價的短期影響。

新聞標題：
{headlines}

請以 JSON 格式回傳（只回傳 JSON，不要其他文字）：
{{
  "overall_score": <-1.0 到 +1.0 的小數，代表整體情緒>,
  "confidence": <0.0 到 1.0，代表你對評分的把握度>,
  "positive_count": <正面新聞數量>,
  "negative_count": <負面新聞數量>,
  "neutral_count": <中性新聞數量>,
  "key_themes": [<3個以內的主要主題>],
  "risk_signals": [<發現的風險信號，若無則為空列表>],
  "opportunity_signals": [<發現的機會信號，若無則為空列表>],
  "summary": "<用中文寫的2-3句情緒摘要>"
}}

評分標準：
+0.8 到 +1.0：極度正面（重大利多、超越預期）
+0.3 到 +0.8：正面（業績成長、新合約）
-0.3 到 +0.3：中性（一般公告）
-0.8 到 -0.3：負面（業績下滑、競爭）
-1.0 到 -0.8：極度負面（醜聞、重大損失）"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # 清除可能的 markdown 包裹
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])

        data = json.loads(text)
        data["news_count"] = len(news_items)
        data["ticker"] = ticker
        return data

    except json.JSONDecodeError:
        return {
            "error": "AI 回傳格式錯誤",
            "raw": response.text[:200] if 'response' in dir() else "",
        }
    except Exception as e:
        return {"error": str(e)}


def run_sentiment_analysis(
    ticker: str,
    company_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    完整情緒分析流程：抓新聞 → AI 評分 → 回傳結構化結果
    """
    if company_name is None:
        company_name = ticker

    # 1. 抓新聞
    news = fetch_news(ticker, max_items=10)

    # 2. AI 情緒評分
    sentiment = score_sentiment_with_ai(ticker, company_name, news)

    # 3. 情緒信號（可作為輔助投資建議）
    score = sentiment.get("overall_score", 0)
    if isinstance(score, (int, float)):
        if score > 0.5:
            signal = "情緒偏多 - 新聞面支持買入"
        elif score < -0.5:
            signal = "情緒偏空 - 新聞面建議謹慎"
        else:
            signal = "情緒中性 - 新聞面無明顯方向"
    else:
        signal = "無法判斷"

    return {
        "ticker": ticker,
        "news_items": news,
        "sentiment_score": sentiment,
        "trading_signal": signal,
        "disclaimer": (
            "情緒分析僅供參考，不構成投資建議。"
            "新聞情緒與股價走勢相關性因股票而異。"
        ),
    }
