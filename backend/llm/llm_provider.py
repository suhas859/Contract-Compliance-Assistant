import os
from abc import ABC, abstractmethod
from collections.abc import Iterator
import json
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

    @abstractmethod
    def stream(self, prompt: str) -> Iterator[str]:
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

    def stream(self, prompt: str) -> Iterator[str]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        with requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
            },
            timeout=120,
            stream=True,
        ) as response:
            response.raise_for_status()
            # The default 512-byte chunk size makes short model tokens appear
            # in large batches instead of streaming as they arrive.
            for line in response.iter_lines(chunk_size=1, decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    break
                data = json.loads(payload)
                token = data["choices"][0].get("delta", {}).get("content")
                if token:
                    yield token

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

    def stream(self, prompt: str) -> Iterator[str]:
        with requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": True},
            timeout=120,
            stream=True,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines(chunk_size=1, decode_unicode=True):
                if not line:
                    continue
                data = json.loads(line)
                token = data.get("response")
                if token:
                    yield token
                if data.get("done"):
                    break
