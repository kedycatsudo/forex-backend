import requests


def query_ollama(prompt: str, model: str = "mistral") -> str:
    print("ollama_query function hitted in ollama.py")
    payload = {"model": model, "prompt": prompt, "stream": False}
    print("payload", payload)
    response = requests.post("http://localhost:11434/api/generate", json=payload)
    print(response)
    response.raise_for_status()
    result = response.json()
    return result.get("response", "").strip()
