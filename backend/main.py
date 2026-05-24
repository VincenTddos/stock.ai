import json
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()  # Load .env before anything else

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
from typing import List

from services.financial_data import get_stock_data
from services.claude_analysis import analyze_stock_stream
from services.data_science.pipeline import run_correlation_analysis, run_signal_pipeline
from services.data_science.unsupervised import run_pca, run_market_regime
from services.data_science.factors import run_factor_analysis
from services.data_science.sentiment import run_sentiment_analysis
from services.data_science.features import test_stationarity
from services.data_science.fetcher import align_tw_us


class CorrelationRequest(BaseModel):
    tw_tickers: List[str] = ["^TWII", "2330.TW", "0050.TW"]
    us_tickers: List[str] = ["SPY", "QQQ", "^VIX"]
    period: str = "3y"
    rolling_window: int = 30


class SignalRequest(BaseModel):
    target: str = "2330.TW"
    features: List[str] = ["^TWII", "SPY", "QQQ", "^VIX", "^GSPC"]
    period: str = "4y"
    train_ratio: float = 0.75


class SentimentRequest(BaseModel):
    ticker: str
    company_name: str = ""


class FactorRequest(BaseModel):
    tw_tickers: List[str] = ["2330.TW", "0050.TW"]
    market_ticker: str = "SPY"
    period: str = "2y"


class StationarityRequest(BaseModel):
    tickers: List[str] = ["2330.TW", "SPY", "^VIX"]
    period: str = "3y"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Stock.AI Backend started")
    yield
    print("👋 Stock.AI Backend stopped")


app = FastAPI(title="Stock.AI API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "Stock.AI Backend is running"}


@app.get("/api/stock/{ticker}")
async def get_stock_info(ticker: str):
    """Fetch stock data from Yahoo Finance"""
    try:
        data = await get_stock_data(ticker.upper())
        # Remove heavy history data from the stock info response
        data_light = {k: v for k, v in data.items()
                      if k not in ("financialsHistory", "cashflowHistory", "balanceSheetHistory")}
        return data_light
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法取得股票數據：{str(e)}")


# Map string section IDs (from frontend) to prompt numbers (1-7)
SECTION_MAP = {
    "overview":   1,
    "financials": 2,
    "moat":       3,
    "valuation":  4,
    "growth":     5,
    "debate":     6,
    "investment": 7,
}


@app.post("/api/analyze/{ticker}/{section}")
async def stream_analysis(ticker: str, section: str):
    """
    Stream AI analysis via Server-Sent Events (SSE).
    section: string ('overview'|'financials'|...) or numeric string ('1'-'7').
    """
    # Resolve section to int
    if section in SECTION_MAP:
        section_num = SECTION_MAP[section]
    else:
        try:
            section_num = int(section)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"無效的 section：{section}")

    if section_num < 1 or section_num > 7:
        raise HTTPException(status_code=400, detail="section 必須介於 1-7 之間")

    try:
        # Fetch full stock data (with history) for analysis
        stock_data = await get_stock_data(ticker.upper())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法取得股票數據：{str(e)}")

    async def event_stream():
        try:
            async for chunk in analyze_stock_stream(ticker, section_num, stock_data):
                payload = json.dumps({"text": chunk}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            error_payload = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ─────────────────────────────────────────────
# Data Science Endpoints
# ─────────────────────────────────────────────

@app.post("/api/ds/correlation")
async def ds_correlation(req: CorrelationRequest):
    """台美股相關性分析（靜態矩陣、滾動相關、Granger 因果、落後期）"""
    loop = __import__("asyncio").get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: run_correlation_analysis(
                req.tw_tickers, req.us_tickers,
                req.period, req.rolling_window
            ),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"相關性分析失敗：{e}")


@app.post("/api/ds/signals")
async def ds_signals(req: SignalRequest):
    """
    Walk-Forward ML 投資信號生成
    防洩漏措施：
      - 特徵全部 shift(1)
      - Scaler 只 fit 訓練集
      - 時間序列切分
      - Walk-Forward 驗證
    """
    loop = __import__("asyncio").get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: run_signal_pipeline(
                req.target, req.features,
                req.period, req.train_ratio,
            ),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"信號生成失敗：{e}")


@app.post("/api/ds/sentiment")
async def ds_sentiment(req: SentimentRequest):
    """新聞情緒分析（yfinance 新聞 + Gemini AI 評分）"""
    loop = __import__("asyncio").get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: run_sentiment_analysis(req.ticker, req.company_name or req.ticker),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"情緒分析失敗：{e}")


@app.post("/api/ds/factors")
async def ds_factors(req: FactorRequest):
    """多因子模型：Alpha、Beta、動量因子、低信噪比說明"""
    loop = __import__("asyncio").get_event_loop()
    try:
        data = await loop.run_in_executor(
            None,
            lambda: align_tw_us(req.tw_tickers, [req.market_ticker], req.period),
        )
        result = await loop.run_in_executor(
            None,
            lambda: run_factor_analysis(data["returns"], req.tw_tickers, req.market_ticker),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"因子分析失敗：{e}")


@app.post("/api/ds/stationarity")
async def ds_stationarity(req: StationarityRequest):
    """ADF 定態性檢定（時間序列分析必要前置步驟）"""
    loop = __import__("asyncio").get_event_loop()
    try:
        all_tw = [t for t in req.tickers if ".TW" in t or "^TW" in t]
        all_us = [t for t in req.tickers if ".TW" not in t and "^TW" not in t]
        if not all_us:
            all_us = req.tickers
            all_tw = []
        data = await loop.run_in_executor(
            None,
            lambda: align_tw_us(all_tw or req.tickers, all_us, req.period),
        )
        result = await loop.run_in_executor(
            None,
            lambda: test_stationarity(data["returns"]),
        )
        return {"stationarity_tests": result, "tickers": req.tickers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"定態性檢定失敗：{e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
