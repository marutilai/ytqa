import os
import json
import numpy as np
import faiss
from typing import List, Dict, Any, Optional
from ...config import CACHE_DIR


class FAISSStore:
    """FAISS vector store with caching."""

    def __init__(self, dimension: int, cache_dir: str = None):
        self.dimension = dimension
        self.cache_dir = cache_dir or CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)

        # Initialize empty index
        self.index = faiss.IndexFlatL2(dimension)
        self.metadata = []
        self.index_path = os.path.join(self.cache_dir, "index.faiss")
        self.metadata_path = os.path.join(self.cache_dir, "metadata.json")

        # Load existing index and metadata if available
        self._load_index()

    def _load_index(self):
        """Load existing index and metadata from cache if available."""
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            print(f"Loading existing FAISS index from {self.index_path}")
            self.index = faiss.read_index(self.index_path)
            with open(self.metadata_path, "r") as f:
                self.metadata = json.load(f)
            print(f"Loaded {len(self.metadata)} vectors from cache")

    def _save_index(self):
        """Save current index and metadata to cache."""
        print(f"Saving FAISS index to {self.index_path}")
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, "w") as f:
            json.dump(self.metadata, f)

    def _get_video_metadata(self, video_id: str) -> List[Dict[str, Any]]:
        """Get all metadata entries for a specific video."""
        return [m for m in self.metadata if m.get("video_id") == video_id]

    def _vectors_exist(self, video_id: str) -> bool:
        """Check if vectors for a video already exist in the store."""
        return len(self._get_video_metadata(video_id)) > 0

    def add_vectors(self, vectors: np.ndarray, metadata: List[Dict[str, Any]]):
        """Add vectors and their metadata to the store if they don't already exist."""
        if len(vectors) != len(metadata):
            raise ValueError("Number of vectors must match number of metadata entries")

        # Check if we already have vectors for this video
        video_id = metadata[0].get("video_id")
        if video_id and self._vectors_exist(video_id):
            print(f"Vectors for video {video_id} already exist in the store, skipping")
            return

        print(f"Adding {len(vectors)} new vectors to the store")
        # Add vectors to index
        self.index.add(vectors)

        # Add metadata
        self.metadata.extend(metadata)

        # Save to cache
        self._save_index()

    def search(self, query_vector: np.ndarray, k: int = 5) -> List[Dict[str, Any]]:
        """Search for nearest neighbors and return their metadata."""
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)

        # Search the index
        distances, indices = self.index.search(query_vector, k)

        # Get metadata for results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.metadata):  # Check if index is valid
                result = self.metadata[idx].copy()
                result["distance"] = float(distances[0][i])
                results.append(result)

        return results

    def get_all_vectors(self) -> np.ndarray:
        """Get all vectors in the store."""
        return self.index.reconstruct_n(0, self.index.ntotal)

    def get_all_metadata(self) -> List[Dict[str, Any]]:
        """Get all metadata in the store."""
        return self.metadata.copy()

    def clear(self):
        """Clear the store and remove cached files."""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
        if os.path.exists(self.metadata_path):
            os.remove(self.metadata_path)
