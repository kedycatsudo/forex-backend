import requests


def query_ollama(prompt: str, model: str = "mistral") -> str:
    payload = {"model": model, "prompt": prompt, "stream": False}
    response = requests.post("http://localhost:11434/api/generate", json=payload)
    response.raise_for_status()
    result = response.json()
    return result.get("response", "").strip()
