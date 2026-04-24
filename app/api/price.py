from fastapi import APIRouter, Query
from app.services.tradingview import fetch_current_price


router = APIRouter()


@router.get("/price")
async def get_price(
    symbol: str = Query(..., example="BINANCE:BTCUSDT"),
    timeframe: int = Query(1),
    range_: int = Query(1),
):
    result = await fetch_current_price(symbol, timeframe, range_)

    return result
