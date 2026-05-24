import os
import google.generativeai as genai
from typing import AsyncGenerator
from .financial_data import format_financial_summary
from .prompts import get_prompt, SYSTEM_PROMPT

_model = None


def get_model() -> genai.GenerativeModel:
    global _model
    if _model is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 環境變數未設定，請在 .env 填入你的 Google Gemini API Key。\n取得方式：https://aistudio.google.com/app/apikey")
        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel(
            model_name=os.environ.get("GEMINI_MODEL", "gemini-1.5-flash"),
            system_instruction=SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                max_output_tokens=4096,
                temperature=0.7,
            ),
        )
    return _model


async def analyze_stock_stream(
    ticker: str,
    section: int,
    stock_data: dict,
) -> AsyncGenerator[str, None]:
    """
    Stream Gemini analysis for a given stock and section.
    Yields text chunks as they arrive from the API.
    """
    model = get_model()
    financial_summary = format_financial_summary(stock_data)
    company_name = stock_data.get("name", ticker)
    prompt = get_prompt(section, ticker, company_name, financial_summary)

    response = await model.generate_content_async(prompt, stream=True)

    async for chunk in response:
        if chunk.text:
            yield chunk.text
