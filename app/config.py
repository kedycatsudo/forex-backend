import os
from dotenv import load_dotenv

load_dotenv()  # loads the variables from .env into environment

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "tradingview-data1.p.rapidapi.com")
