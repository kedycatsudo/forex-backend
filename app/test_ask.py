# test_ask.py

import requests
import json

prompt = """You are a trading expert. Given the following "task" and "data," 
write a thorough review. 

Respond with a JSON in this format: 
{
  "General Review for the current data": "...", 
  "Review for short term long position": "...",
  "Review for short term short position": "...",
  "Recommendation between short and long position": "..."
}

Task: analyze the candlesticks
Data:
Market: BTCUSD
Timeframe: 15m
Period: Last 25 candles
Indicators: RSI (14), EMA (50)
OHLCV:\n[[66500, 66650, 66480, 66620, 1200],\n [66620, 66720, 66590, 66700, 1350],\n [66700, 66850, 66680, 66820, 1400],\n [66820, 66970, 66750, 66950, 1500],\n [66950, 67100, 66910, 67080, 1430],\n [67080, 67150, 67020, 67110, 1600],\n [67110, 67250, 67080, 67220, 1680],\n [67220, 67380, 67200, 67350, 1720],\n [67350, 67490, 67290, 67460, 1800],\n [67460, 67580, 67420, 67570, 1850],\n [67570, 67720, 67560, 67700, 1920],\n [67700, 67880, 67690, 67830, 1950],\n [67830, 68010, 67800, 67990, 1970],\n [67990, 68130, 67950, 68110, 2090],\n [68110, 68250, 68090, 68230, 2200],\n [68230, 68380, 68190, 68360, 2240],\n [68360, 68510, 68350, 68490, 2290],\n [68490, 68620, 68450, 68590, 2330],\n [68590, 68780, 68560, 68740, 2370],\n [68740, 68920, 68710, 68890, 2450],\n [68890, 69100, 68840, 69080, 2530],\n [69080, 69220, 69080, 69200, 2600],\n [69200, 69340, 69180, 69310, 2700],\n [69310, 69480, 69300, 69470, 2800],\n [69470, 69600, 69460, 69590, 2900]]
RSI: 68
EMA(50): 68500e
"""

resp = requests.post(
    "http://127.0.0.1:8000/agent/ask", json={"prompt": prompt, "model": "mistral"}
)
result = resp.json()
ai_reply = result["llm_response"]

try:
    parsed = json.loads(ai_reply)
except Exception:
    parsed = {"raw": ai_reply}

# Nicely formatted print:
print(
    "\n=== General Review ===\n" + parsed.get("General Review for the current data", "")
)
print(
    "\n=== Short-term LONG Review ===\n"
    + parsed.get("Review for short term long position", "")
)
print(
    "\n=== Short-term SHORT Review ===\n"
    + parsed.get("Review for short term short position", "")
)
print(
    "\n=== RECOMMENDATION ===\n"
    + parsed.get("recommendation between short and long position", "")
)
