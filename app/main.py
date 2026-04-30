from fastapi import FastAPI
from pydantic import BaseModel
from app.api.price import router as price_router  # adjust import as needed
from app.services.ollama import query_ollama

app = FastAPI()
app.include_router(price_router)


class PromptRequest(BaseModel):
    prompt: str
    model: str = "mistral"  # typo fixed from "mistrl"


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.get("/agent/test")
def test_agent_greeting():
    prompt = "Hi"
    reply = query_ollama(prompt=prompt)
    return {"llm_response": reply}


@app.post("/agent/ask")
def ask_agent(data: PromptRequest):
    reply = query_ollama(prompt=data.prompt, model=data.model)
    return {"llm_response": reply}
