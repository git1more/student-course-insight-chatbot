import time

from openai import APIConnectionError, RateLimitError
from openai import OpenAI
from app.core.config import settings


class EmbeddingService:
    def __init__(self):
        self._client = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=settings.embedding_api_key or settings.openai_api_key,
                base_url=settings.embedding_base_url or None,
            )
        return self._client

    @staticmethod
    def _with_retry(call, attempts: int = 5, base_delay: float = 2.0):
        """Retry on 429 / connection errors — free provider tiers throttle hard."""
        for i in range(attempts):
            try:
                return call()
            except (RateLimitError, APIConnectionError) as exc:
                if i == attempts - 1:
                    raise
                wait = base_delay * (2 ** i)
                print(
                    f'[embedding] {type(exc).__name__} — retry {i + 1}/{attempts - 1} '
                    f'in {wait:.0f}s',
                    flush=True,
                )
                time.sleep(wait)

    def embed_text(self, text: str) -> list[float]:
        """Embed a single string."""
        response = self._with_retry(
            lambda: self.client.embeddings.create(
                model=settings.embedding_model,
                input=text.replace('\n', ' '),
                dimensions=settings.embedding_dimensions,
            )
        )
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of strings (batch size is provider-limited)."""
        cleaned = [t.replace('\n', ' ') for t in texts]
        response = self._with_retry(
            lambda: self.client.embeddings.create(
                model=settings.embedding_model,
                input=cleaned,
                dimensions=settings.embedding_dimensions,
            )
        )
        # Results are returned in the same order
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


embedding_service = EmbeddingService()
