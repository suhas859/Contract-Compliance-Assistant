import os
from abc import ABC, abstractmethod
from pathlib import Path

import requests
from dotenv import load_dotenv


# Explicit path: bare load_dotenv() only searches upward from the current
# working directory for a file named ".env" -- it won't find backend/.env
# when the server is launched from the repo root (the normal case here).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class LLMProvider(ABC):

    @abstractmethod
    def generate(self, prompt: str) -> str:
        ...

class OpenAILLM(LLMProvider):
    """
    Talks to the OpenAI API.
    """

    def __init__(self, model: str | None = None, api_key: str | None = None):
            self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=120,
        )
        if not response.ok:
            try:
                error_message = response.json()["error"]["message"]
            except (KeyError, TypeError, ValueError):
                error_message = response.reason
            raise RuntimeError(
                f"OpenAI request failed ({response.status_code}): {error_message}"
            )
        return response.json()["choices"][0]["message"]["content"].strip()

class OllamaLLM(LLMProvider):
    """
    Talks to a local Ollama server over its HTTP API.
    """

    def __init__(self, model: str | None = None, base_url: str | None = None):
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.2:1b")
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
