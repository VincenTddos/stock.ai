import yfinance as yf
import pandas as pd
from typing import Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

executor = ThreadPoolExecutor(max_workers=4)


def _fetch_stock_data(ticker: str) -> Dict[str, Any]:
    """Fetch comprehensive stock data from Yahoo Finance (sync).
    yfinance 1.3+ uses curl_cffi internally for browser-like requests.
    """
    last_err = None
    for attempt in range(3):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            break
        except Exception as e:
            last_err = e
            if attempt < 2:
                time.sleep(2 ** attempt)
    else:
        raise ValueError(f"Yahoo Finance 暫時無法取得 {ticker} 資料，請稍後再試。錯誤：{last_err}")


    if not info or info.get("trailingPegRatio") is None and info.get("currentPrice") is None and info.get("regularMarketPrice") is None:
        # Try a basic check
        if not info.get("longName") and not info.get("shortName"):
            raise ValueError(f"找不到股票代號：{ticker}，請確認代號是否正確。")

    def safe(key, default=None):
        val = info.get(key, default)
        if isinstance(val, float) and (val != val):  # NaN check
            return default
        return val

    price = safe("currentPrice") or safe("regularMarketPrice") or safe("navPrice") or 0
    prev_close = safe("previousClose") or safe("regularMarketPreviousClose") or price
    change = price - prev_close if prev_close else 0
    change_pct = (change / prev_close * 100) if prev_close else 0

    data = {
        # Identity
        "ticker": ticker.upper(),
        "name": safe("longName") or safe("shortName") or ticker.upper(),
        "sector": safe("sector", "N/A"),
        "industry": safe("industry", "N/A"),
        "country": safe("country", "N/A"),
        "currency": safe("currency", "USD"),
        "exchange": safe("exchange", "N/A"),
        "description": safe("longBusinessSummary", "N/A"),
        # Price
        "price": price,
        "previousClose": prev_close,
        "change": change,
        "changePercent": change_pct,
        "dayLow": safe("dayLow", 0),
        "dayHigh": safe("dayHigh", 0),
        "week52High": safe("fiftyTwoWeekHigh", 0),
        "week52Low": safe("fiftyTwoWeekLow", 0),
        "volume": safe("volume", 0),
        "avgVolume": safe("averageVolume", 0),
        # Valuation
        "marketCap": safe("marketCap", 0),
        "peRatio": safe("trailingPE"),
        "forwardPE": safe("forwardPE"),
        "priceToBook": safe("priceToBook"),
        "priceToSales": safe("priceToSalesTrailing12Months"),
        "evToRevenue": safe("enterpriseToRevenue"),
        "evToEbitda": safe("enterpriseToEbitda"),
        "peg": safe("pegRatio"),
        # Financials
        "revenue": safe("totalRevenue", 0),
        "revenueGrowth": safe("revenueGrowth", 0),
        "grossMargins": safe("grossMargins", 0),
        "operatingMargins": safe("operatingMargins", 0),
        "profitMargins": safe("profitMargins", 0),
        "ebitda": safe("ebitda", 0),
        "netIncome": safe("netIncomeToCommon", 0),
        "eps": safe("trailingEps", 0),
        "forwardEps": safe("forwardEps", 0),
        "earningsGrowth": safe("earningsGrowth", 0),
        # Balance sheet
        "totalCash": safe("totalCash", 0),
        "totalDebt": safe("totalDebt", 0),
        "debtToEquity": safe("debtToEquity"),
        "currentRatio": safe("currentRatio"),
        "bookValue": safe("bookValue", 0),
        # Cash flow
        "freeCashFlow": safe("freeCashflow", 0),
        "operatingCashFlow": safe("operatingCashflow", 0),
        # profitMargin alias (frontend uses singular form)
        "profitMargin": safe("profitMargins", 0),
        # Returns
        "roe": safe("returnOnEquity"),
        "roa": safe("returnOnAssets"),
        "dividendYield": safe("dividendYield", 0),
        "payoutRatio": safe("payoutRatio", 0),
        # Risk
        "beta": safe("beta"),
        # Analyst
        "targetMeanPrice": safe("targetMeanPrice"),
        "targetHighPrice": safe("targetHighPrice"),
        "targetLowPrice": safe("targetLowPrice"),
        "recommendationMean": safe("recommendationMean"),
        "numberOfAnalystOpinions": safe("numberOfAnalystOpinions", 0),
    }

    # Historical financials
    try:
        financials = stock.financials
        if financials is not None and not financials.empty:
            data["financialsHistory"] = _format_df(financials)
    except Exception:
        data["financialsHistory"] = {}

    try:
        cashflow = stock.cashflow
        if cashflow is not None and not cashflow.empty:
            data["cashflowHistory"] = _format_df(cashflow)
    except Exception:
        data["cashflowHistory"] = {}

    try:
        bs = stock.balance_sheet
        if bs is not None and not bs.empty:
            data["balanceSheetHistory"] = _format_df(bs)
    except Exception:
        data["balanceSheetHistory"] = {}

    return data


def _format_df(df: pd.DataFrame) -> dict:
    """Convert DataFrame to JSON-serializable dict"""
    try:
        result = {}
        for col in df.columns:
            col_str = str(col)[:10]  # date string YYYY-MM-DD
            result[col_str] = {}
            for idx in df.index:
                val = df.loc[idx, col]
                result[col_str][str(idx)] = None if pd.isna(val) else float(val)
        return result
    except Exception:
        return {}


async def get_stock_data(ticker: str) -> Dict[str, Any]:
    """Async wrapper for yfinance fetch"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, _fetch_stock_data, ticker)


def format_financial_summary(data: Dict[str, Any]) -> str:
    """Format stock data into a structured text summary for Claude prompts"""
    cur = data.get("currency", "USD")

    def c(val, decimals=2):
        """Format currency"""
        if val is None or val == 0:
            return "N/A"
        if abs(val) >= 1e12:
            return f"{cur} {val/1e12:.{decimals}f}T"
        elif abs(val) >= 1e9:
            return f"{cur} {val/1e9:.{decimals}f}B"
        elif abs(val) >= 1e6:
            return f"{cur} {val/1e6:.{decimals}f}M"
        else:
            return f"{cur} {val:,.0f}"

    def p(val):
        """Format percentage"""
        if val is None:
            return "N/A"
        return f"{val * 100:.1f}%"

    def n(val, d=2):
        """Format number"""
        if val is None:
            return "N/A"
        return f"{val:.{d}f}x"

    lines = [
        f"=== {data['name']} ({data['ticker']}) ===",
        f"Sector: {data['sector']} | Industry: {data['industry']}",
        f"Exchange: {data['exchange']} | Country: {data['country']}",
        "",
        "--- PRICE ---",
        f"Current Price: {c(data['price'])}",
        f"52W High / Low: {c(data['week52High'])} / {c(data['week52Low'])}",
        f"Market Cap: {c(data['marketCap'])} | Beta: {data.get('beta', 'N/A')}",
        "",
        "--- VALUATION ---",
        f"Trailing P/E: {n(data['peRatio'])} | Forward P/E: {n(data['forwardPE'])}",
        f"Price/Book: {n(data['priceToBook'])} | Price/Sales: {n(data['priceToSales'])}",
        f"EV/Revenue: {n(data['evToRevenue'])} | EV/EBITDA: {n(data['evToEbitda'])}",
        f"PEG Ratio: {n(data['peg'])}",
        "",
        "--- FINANCIALS ---",
        f"Revenue (TTM): {c(data['revenue'])} | YoY Growth: {p(data['revenueGrowth'])}",
        f"EBITDA: {c(data['ebitda'])} | Net Income: {c(data['netIncome'])}",
        f"EPS (TTM): {data.get('eps', 'N/A')} | EPS (Fwd): {data.get('forwardEps', 'N/A')}",
        f"Earnings Growth: {p(data['earningsGrowth'])}",
        "",
        "--- MARGINS ---",
        f"Gross Margin: {p(data['grossMargins'])}",
        f"Operating Margin: {p(data['operatingMargins'])}",
        f"Net Profit Margin: {p(data['profitMargins'])}",
        "",
        "--- BALANCE SHEET ---",
        f"Cash: {c(data['totalCash'])} | Total Debt: {c(data['totalDebt'])}",
        f"Debt/Equity: {n(data['debtToEquity'])} | Current Ratio: {n(data['currentRatio'])}",
        f"Book Value/Share: {data.get('bookValue', 'N/A')}",
        "",
        "--- CASH FLOW ---",
        f"Free Cash Flow: {c(data['freeCashFlow'])}",
        f"Operating Cash Flow: {c(data['operatingCashFlow'])}",
        "",
        "--- RETURNS ---",
        f"ROE: {p(data['roe'])} | ROA: {p(data['roa'])}",
        f"Dividend Yield: {p(data['dividendYield'])} | Payout Ratio: {p(data['payoutRatio'])}",
        "",
        "--- ANALYST CONSENSUS ---",
        f"Price Target: {c(data['targetMeanPrice'])} (Low: {c(data['targetLowPrice'])}, High: {c(data['targetHighPrice'])})",
        f"Rating (1=Strong Buy ~ 5=Strong Sell): {data.get('recommendationMean', 'N/A')}",
        f"Analysts Covering: {data.get('numberOfAnalystOpinions', 0)}",
    ]

    # Append historical income statement (up to 4 years)
    hist = data.get("financialsHistory", {})
    if hist:
        lines.append("")
        lines.append("--- HISTORICAL INCOME STATEMENT (Annual) ---")
        for year, metrics in list(hist.items())[:4]:
            lines.append(f"{year}:")
            key_items = ["Total Revenue", "Gross Profit", "Operating Income",
                         "Net Income", "EBITDA", "Basic EPS"]
            for k in key_items:
                if k in metrics and metrics[k] is not None:
                    lines.append(f"  {k}: {c(metrics[k])}")

    cf = data.get("cashflowHistory", {})
    if cf:
        lines.append("")
        lines.append("--- HISTORICAL CASH FLOW (Annual) ---")
        for year, metrics in list(cf.items())[:4]:
            lines.append(f"{year}:")
            key_items = ["Free Cash Flow", "Operating Cash Flow", "Capital Expenditure"]
            for k in key_items:
                if k in metrics and metrics[k] is not None:
                    lines.append(f"  {k}: {c(metrics[k])}")

    return "\n".join(lines)
