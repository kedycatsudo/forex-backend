from fastapi import APIRouter, Query
from app.services.tradingview import fetch_current_price, fetch_candles
import json


router = APIRouter()


@router.get("/price")
async def get_price(
    symbol: str = Query(..., example="BINANCE:BTCUSDT"),
    timeframe: int = Query(1),
    range: int = Query(1),
):
    result = await fetch_current_price(symbol, timeframe, range)

    return result


@router.get("/candles")
async def get_agent_candles(
    symbol: str = Query(..., example="BINANCE:BTCUSDT"),
    timeframe: int = Query(1, description="Candle size in minutes"),
    range: int = Query(50, description="Number of candles to fetch"),
):
    """
    Return market candles formatted for AI agent analysis.
    """
    result = await fetch_candles(symbol, timeframe, range)

    print(json.dumps(result, indent=2, default=str))
    return result
