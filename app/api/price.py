# app/api/price.py

from fastapi import APIRouter, Query
from app.services.tradingview import fetch_current_price, fetch_candles
from app.services.ollama import query_ollama
import json

router = APIRouter()


@router.get("/price")
async def get_price(
    symbol: str = Query(..., examples="BINANCE:BTCUSDT"),
    timeframe: str = Query("1"),
    range: int = Query(1),
):
    result = await fetch_current_price(symbol, timeframe, range)
    return result


@router.get("/agent/analyze_candles")
async def analyze_candlesticks(
    symbol: str = Query(..., examples="BTCUSD"),
    timeframe: str = Query("15", description="Candle size (e.g. 15m, 1H)"),
    range: int = Query(25, description="Number of candles to analyze"),
):
    """
    Fetch candles and analyze them with Ollama AI agent.
    """
    print("/agent/analyze_candles hitted.")
    try:
        history = await fetch_candles(symbol, timeframe, range)
        print("histroy hitted:", history)
    except Exception as e:
        return {"error": f"Failed to fetch candles: {str(e)}"}

    ohlcv = history.get("OHLCV", [])
    rsi = history.get("RSI", "N/A")
    ema50 = history.get("EMA_50", "N/A")
    macd = history.get("MACD", "N/A")
    macd_signal = history.get("MACD_signal", "N/A")
    macd_hist = history.get("MACD_hist", "N/A")

    prompt = f"""
You are a trading machine with 80% profit rate. Will be given you trading tasks will be expected output respond with a JSON in this format: 
{{
  "General Review for the current data": "...",
  "Review for short term long position": "...",
  "Review for short term short position": "...",
  "Recommendation between short and long position": "..."
}}

Task:Analyze the candles considering with followings;
Data:
Market: {symbol.upper()}
Timeframe: {timeframe}
Period: Last {range} candles
Indicators: RSI (14), EMA (50)
OHLCV: {json.dumps(ohlcv)}
RSI: {rsi}
EMA(50): {ema50}
MACD:{macd}
MACD_signal:{macd_signal}
MACD_hist:{macd_hist}
"""
    print("agent requested")

    ai_response = query_ollama(prompt)
    try:
        structured = json.loads(ai_response)
        print("structured", structured)
    except Exception:
        structured = {"raw_analysis": ai_response}
    return {
        "prompt": prompt,
        "llm_analysis": structured,
    }
