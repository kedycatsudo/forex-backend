def calculate_indicators(candles, rsi_period=14, ema_period=50):
    import pandas as pd
    import ta

    df = pd.DataFrame(candles)
    df.columns = [c.lower() for c in df.columns]

    # Old (broken): df = df.fillna(method="ffill")
    df = df.ffill().bfill()  # ← <<======

    rsi = ta.momentum.RSIIndicator(close=df["close"], window=rsi_period).rsi()
    ema = ta.trend.EMAIndicator(close=df["close"], window=ema_period).ema_indicator()
    macd = ta.trend.MACD(close=df["close"])
    return {
        "RSI": float(rsi.iloc[-1]) if len(rsi.dropna()) else None,
        "EMA": float(ema.iloc[-1]) if len(ema.dropna()) else None,
        "MACD": float(macd.macd().iloc[-1]) if len(macd.macd().dropna()) else None,
        "MACD_signal": float(macd.macd_signal().iloc[-1])
        if len(macd.macd_signal().dropna())
        else None,
        "MACD_hist": float(macd.macd_diff().iloc[-1])
        if len(macd.macd_diff().dropna())
        else None,
    }
