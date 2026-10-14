from abc import ABC, abstractmethod
import hashlib
import math

from google import genai
from google.genai import types

from app.core.config import get_settings


class EmbeddingProvider(ABC):

    @abstractmethod
    def embed_text(
        self,
        text: str,
    ) -> list[float]:
        raise NotImplementedError

    def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        return [
            self.embed_text(text)
            for text in texts
        ]


class LocalEmbeddingProvider(EmbeddingProvider):

    def __init__(
        self,
        dimensions: int = 128,
    ):
        self.dimensions = dimensions

    def embed_text(
        self,
        text: str,
    ) -> list[float]:
        vector = []

        for index in range(self.dimensions):
            digest = hashlib.sha256(
                f"{index}:{text}".encode("utf-8")
            ).digest()

            value = int.from_bytes(
                digest[:4],
                byteorder="big",
            )

            normalized = (
                (value / 2**32) * 2
            ) - 1

            vector.append(normalized)

        magnitude = math.sqrt(
            sum(value * value for value in vector)
        )

        if magnitude == 0:
            return vector

        return [
            value / magnitude
            for value in vector
        ]


class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Semantic embedding provider using Google's Gemini Embedding API.
    """

    def __init__(
        self,
        model: str = "gemini-embedding-2",
        dimensions: int = 128,
    ):
        settings = get_settings()

        if not settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured."
            )

        self.model = model
        self.dimensions = dimensions

        self.client = genai.Client(
            api_key=settings.gemini_api_key,
        )

    def embed_text(
        self,
        text: str,
    ) -> list[float]:
        if not text.strip():
            return [0.0] * self.dimensions

        result = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config=types.EmbedContentConfig(
                output_dimensionality=self.dimensions,
            ),
        )

        if not result.embeddings:
            raise RuntimeError(
                "Gemini returned no embedding."
            )

        values = result.embeddings[0].values

        if values is None:
            raise RuntimeError(
                "Gemini returned an empty embedding."
            )

        if len(values) != self.dimensions:
            raise RuntimeError(
                "Gemini returned an unexpected "
                f"embedding dimension: {len(values)}"
            )

        return list(values)