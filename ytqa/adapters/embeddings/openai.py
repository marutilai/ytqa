import os
import json
from typing import List
import numpy as np

import openai
from ...config import CACHE_DIR
from ytqa.adapters.vectorstores.faiss_store import FAISSVectorStore


class OpenAIEmbeddings:
    """Provider for OpenAI text embeddings with caching."""

    def __init__(self, api_key: str = None, cache_dir: str = None):
        if api_key:
            openai.api_key = api_key
        elif not openai.api_key:
            raise ValueError(
                "OpenAI API key must be provided or set in OPENAI_API_KEY environment variable"
            )
        self.cache_dir = (
            cache_dir
            or CACHE_DIR
            or os.path.join(os.path.dirname(CACHE_DIR), "embeddings_cache")
        )
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cached_path(self, text: str) -> str:
        """Get path for cached embedding."""
        # Create a hash of the text to use as filename
        import hashlib

        text_hash = hashlib.md5(text.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{text_hash}.json")

    def _load_cached_embedding(self, text: str) -> List[float]:
        """Load cached embedding if it exists."""
        cache_path = self._get_cached_path(text)
        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                return json.load(f)
        return None

    def _save_cached_embedding(self, text: str, embedding: List[float]):
        """Save embedding to cache."""
        cache_path = self._get_cached_path(text)
        with open(cache_path, "w") as f:
            json.dump(embedding, f)

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text, using cache if available."""
        # Check cache first
        cached_embedding = self._load_cached_embedding(text)
        if cached_embedding is not None:
            return cached_embedding

        # If not in cache, get from OpenAI
        response = openai.embeddings.create(
            model="text-embedding-3-large", input=text, encoding_format="float"
        )
        embedding = response.data[0].embedding

        # Cache the result
        self._save_cached_embedding(text, embedding)
        return embedding

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts, using cache where available."""
        embeddings = []
        uncached_texts = []
        uncached_indices = []

        # Check cache for each text
        for i, text in enumerate(texts):
            cached_embedding = self._load_cached_embedding(text)
            if cached_embedding is not None:
                embeddings.append(cached_embedding)
            else:
                embeddings.append(None)  # Placeholder
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Get embeddings for uncached texts
        if uncached_texts:
            response = openai.embeddings.create(
                model="text-embedding-3-large",
                input=uncached_texts,
                encoding_format="float",
            )

            # Update embeddings and cache results
            for i, embedding in enumerate(response.data):
                idx = uncached_indices[i]
                embeddings[idx] = embedding.embedding
                self._save_cached_embedding(uncached_texts[i], embedding.embedding)

        return embeddings
