from openai import OpenAI
from app.core.config import settings


class EmbeddingService:
    def __init__(self):
        self._client = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client

    def embed_text(self, text: str) -> list[float]:
        """Embed a single string."""
        response = self.client.embeddings.create(
            model=settings.embedding_model,
            input=text.replace('\n', ' '),
        )
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed up to 2048 strings in one API call."""
        cleaned = [t.replace('\n', ' ') for t in texts]
        response = self.client.embeddings.create(
            model=settings.embedding_model,
            input=cleaned,
        )
        # Results are returned in the same order
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


embedding_service = EmbeddingService()
