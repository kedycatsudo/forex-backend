from app.config import RAPIDAPI_KEY, RAPIDAPI_HOST
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
        data = response.json()  # we can furter validate or parse here
        return data


async def fetch_candles(symbol: str, timeframe: str = "1", range_: int = 10):
    url_path = f"/api/price/{symbol}"
    params = {"timeframe": timeframe, "range": range_}
    headers = get_headers()

    async with httpx.AsyncClient(base_url=f"https://{RAPIDAPI_HOST}") as client:
        response = await client.get(url_path, params=params, headers=headers)
        response.raise_for_status()
        api_data = response.json()

    # Get the history
    history = api_data["data"]["history"]

    candles = []
    for candle in history:
        candles.append(
            {
                "timestamp": candle["time"],
                "open": candle["open"],
                "close": candle["close"],
                "high": candle["max"],
                "low": candle["min"],
                "volume": candle["volume"],
            }
        )

    # Optionally append the current candle at the end
    if "current" in api_data["data"]:
        c = api_data["data"]["current"]
        candles.append(
            {
                "timestamp": c["time"],
                "open": c["open"],
                "close": c["close"],
                "high": c["max"],
                "low": c["min"],
                "volume": c["volume"],
            }
        )

    return {"symbol": symbol, "timeframe": timeframe, "candles": candles}
