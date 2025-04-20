import os
import json
import numpy as np
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

from .adapters.transcripts.factory import TranscriptFactory
from .adapters.embeddings.openai import OpenAIEmbeddings
from .adapters.vectorstores.faiss_store import FAISSStore
from .core.models import Segment
from .core.qa import answer


class Orchestrator:
    """Orchestrates the workflow between different adapters."""

    def __init__(self, openai_api_key: Optional[str] = None):
        # Initialize transcript factory
        self.transcript_factory = TranscriptFactory(openai_api_key=openai_api_key)

        # Initialize embeddings provider
        self.embeddings = OpenAIEmbeddings(api_key=openai_api_key)

        # Initialize vector store (3072 is the dimension for text-embedding-3-large)
        self.vector_store = FAISSStore(dimension=3072)

    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL."""
        parsed = urlparse(url)
        if parsed.hostname in ["youtube.com", "www.youtube.com"]:
            if parsed.path == "/watch":
                return parse_qs(parsed.query)["v"][0]
        elif parsed.hostname in ["youtu.be", "www.youtu.be"]:
            return parsed.path[1:]
        raise ValueError(f"Invalid YouTube URL: {url}")

    def process_video(self, video_url: str) -> Dict[str, Any]:
        """Process a video: get transcript, create embeddings, and store in vector store."""
        try:
            # Extract video ID from URL
            video_id = self._extract_video_id(video_url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")

            # Get transcript (TranscriptFactory handles merging and caching)
            print(f"Getting transcript for video {video_id}")
            chunks = self.transcript_factory.get_transcript(video_id)
            if not chunks:
                raise ValueError("Failed to get transcript")

            # Create embeddings for chunks
            print(f"Creating embeddings for {len(chunks)} chunks")
            embeddings = self.embeddings.get_embeddings(
                [chunk.text for chunk in chunks]
            )

            # Prepare metadata for vector store
            metadata = [
                {
                    "video_id": video_id,
                    "text": chunk.text,
                    "start": chunk.start,
                    "duration": chunk.duration,
                    "chunk_index": i,
                }
                for i, chunk in enumerate(chunks)
            ]

            # Add to vector store (FAISSStore will handle caching)
            print(f"Adding vectors to store for video {video_id}")
            self.vector_store.add_vectors(np.array(embeddings), metadata)

            # Return the first 5 segments for reference
            segments = [
                {
                    "text": chunk.text,
                    "start": chunk.start,
                    "duration": chunk.duration,
                }
                for chunk in chunks[:5]
            ]

            return {
                "video_id": video_id,
                "num_segments": len(chunks),
                "segments": segments,
            }

        except Exception as e:
            print(f"Error processing video: {str(e)}")
            raise

    def search_transcript(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search the transcript using the query text."""
        # Get embedding for query
        query_embedding = self.embeddings.get_embedding(query)

        # Search vector store
        results = self.vector_store.search(np.array(query_embedding), k=k)

        return results

    def get_video_transcript(self, video_id: str) -> List[Dict[str, Any]]:
        """Get transcript for a specific video."""
        # Get all metadata from vector store
        all_metadata = self.vector_store.get_all_metadata()

        # Filter for the specific video
        video_segments = [
            metadata for metadata in all_metadata if metadata["video_id"] == video_id
        ]

        # Sort by start time
        video_segments.sort(key=lambda x: x["start"])

        return video_segments

    def answer_question(
        self, query: str, video_id: Optional[str] = None, k: int = 5
    ) -> str:
        """
        Answer a question about a video's content.

        Args:
            query: The question to answer
            video_id: Optional video ID to restrict search to
            k: Number of chunks to retrieve for context

        Returns:
            str: Generated answer with relevant timestamps
        """
        # Get relevant chunks
        chunks = self.search_transcript(query, k=k)

        # Filter by video_id if specified
        if video_id:
            chunks = [chunk for chunk in chunks if chunk["video_id"] == video_id]

        # Generate answer using the QA module
        return answer(query, chunks)
