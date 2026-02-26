"""LLM integration service using Ollama for local inference."""

import httpx
import json
import logging
import time
from typing import Optional, AsyncGenerator
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMService:
    """Service for interacting with Ollama-hosted LLMs."""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.embed_model = settings.OLLAMA_EMBED_MODEL
        self._available = None
        self._available_checked_at = 0.0

    async def is_available(self) -> bool:
        """Check if Ollama is running and the model is available (cached for 60s)."""
        now = time.time()
        if self._available is not None and (now - self._available_checked_at) < 60:
            return self._available
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    model_names = [m.get("name", "").split(":")[0] for m in models]
                    self._available = self.model in model_names
                    self._available_checked_at = now
                    return self._available
        except Exception:
            self._available = False
            self._available_checked_at = now
        return False

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Generate a completion from the LLM."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        },
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return f"[LLM unavailable] Error: {str(e)}"

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> AsyncGenerator[str, None]:
        """Stream a completion from the LLM."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": True,
                        "options": {"temperature": temperature},
                    },
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                            if data.get("done", False):
                                break
        except Exception as e:
            logger.error(f"LLM stream error: {e}")
            yield f"[LLM unavailable] Error: {str(e)}"

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        embeddings = []
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                for text in texts:
                    resp = await client.post(
                        f"{self.base_url}/api/embeddings",
                        json={"model": self.embed_model, "prompt": text},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    embeddings.append(data.get("embedding", []))
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            # Return zero vectors as fallback
            embeddings = [[0.0] * 768 for _ in texts]
        return embeddings


# Singleton instance
llm_service = LLMService()
