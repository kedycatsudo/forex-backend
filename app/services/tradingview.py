from app.config import RAPIDAPI_KEY, RAPIDAPI_HOST
import httpx


def get_headers():
    return {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
        "Content-Type": "application/json",
    }


async def fetch_current_price(symbol: str, timeframe: int = 1, range_: int = 1):
    url_path = f"/api/price/{symbol}"
    params = {"timeframe": timeframe, "range": range_}
    headers = get_headers()

    async with httpx.AsyncClient(base_url=f"https://{RAPIDAPI_HOST}") as client:
        response = await client.get(url_path, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()  # we can furter validate or parse here
        return data
