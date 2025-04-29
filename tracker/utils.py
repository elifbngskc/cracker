import requests
from django.conf import settings

def query_ollama(prompt, model="llama3"):
    """
    Ollama sunucusuna istek atar ve modeli çalıştırarak yanıt döner.
    """
    url = f"{settings.OLLAMA_API_URL}/api/generate"
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False  # stream True olursa yanıt satır satır gelir
    }

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json().get("response", "")  # sadece yanıt metnini döndür
    except requests.RequestException as e:
        return f"Ollama bağlantı hatası: {e}"
