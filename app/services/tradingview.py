# app/services/tradingview.py

from app.config import RAPIDAPI_KEY, RAPIDAPI_HOST
from app.services.indicators import calculate_indicators
import httpx


def get_headers():
    return {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
        "Content-Type": "application/json",
    }


async def fetch_current_price(symbol: str, timeframe: str = "1", range: int = 1):
    url_path = f"/api/price/{symbol}"
    params = {"timeframe": timeframe, "range": range}
    headers = get_headers()
    async with httpx.AsyncClient(base_url=f"https://{RAPIDAPI_HOST}") as client:
        response = await client.get(url_path, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data


async def fetch_candles(symbol: str, timeframe: str = "1", range: int = 10):
    url_path = f"/api/price/{symbol}"
    params = {"timeframe": timeframe, "range": range}
    headers = get_headers()
    async with httpx.AsyncClient(base_url=f"https://{RAPIDAPI_HOST}") as client:
        response = await client.get(url_path, params=params, headers=headers)
        response.raise_for_status()
        api_data = response.json()
    # Robust key-checks
    if "data" not in api_data or "history" not in api_data["data"]:
        raise ValueError(
            f"Expected ['data']['history'] in API response, got: {api_data}"
        )
    history = api_data["data"]["history"]

    # Build OHLCV list for LLM and a candle list for indicator calculation
    candles = []
    ohlcv = []
    for candle in history:
        candle_obj = {
            "open": candle["open"],
            "high": candle["high"] if "high" in candle else candle.get("max"),
            "low": candle["low"] if "low" in candle else candle.get("min"),
            "close": candle["close"],
            "volume": candle["volume"],
        }
        candles.append(candle_obj)
        ohlcv.append(
            [
                candle_obj["open"],
                candle_obj["high"],
                candle_obj["low"],
                candle_obj["close"],
                candle_obj["volume"],
            ]
        )

    # Optionally append current candle
    if "current" in api_data["data"]:
        c = api_data["data"]["current"]
        c_obj = {
            "open": c["open"],
            "high": c["high"] if "high" in c else c.get("max"),
            "low": c["low"] if "low" in c else c.get("min"),
            "close": c["close"],
            "volume": c["volume"],
        }
        candles.append(c_obj)
        ohlcv.append(
            [
                c_obj["open"],
                c_obj["high"],
                c_obj["low"],
                c_obj["close"],
                c_obj["volume"],
            ]
        )

    # Calculate indicators using all candles
    ind = (
        calculate_indicators(candles)
        if len(candles) >= 50
        else {
            "RSI": None,
            "EMA": None,
            "MACD": None,
            "MACD_signal": None,
            "MACD_hist": None,
        }
    )

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "OHLCV": ohlcv,
        "RSI": ind["RSI"],
        "EMA_50": ind["EMA"],
        "MACD": ind["MACD"],
        "MACD_signal": ind["MACD_signal"],
        "MACD_hist": ind["MACD_hist"],
    }
