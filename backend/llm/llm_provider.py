import os
from abc import ABC, abstractmethod

import requests


class LLMProvider(ABC):

    @abstractmethod
    def generate(self, prompt: str) -> str:
        ...


class OllamaLLM(LLMProvider):
    """
    Talks to a local Ollama server over its HTTP API.
    """

    def __init__(self, model: str | None = None, base_url: str | None = None):
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3")
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    def generate(self, prompt: str) -> str:
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["response"].strip()
