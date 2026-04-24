from fastapi import FastAPI
from app.api.price import router as price_router

app = FastAPI()
app.include_router(price_router)


@app.get("/")
def health_check():
    return {"status": "ok"}
