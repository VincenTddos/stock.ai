import json
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()  # Load .env before anything else

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from services.financial_data import get_stock_data
from services.claude_analysis import analyze_stock_stream


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
