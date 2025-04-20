import os
import json
import numpy as np
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

from ..adapters.transcripts.factory import TranscriptFactory
from ..adapters.embeddings.openai import OpenAIEmbeddings
from ..adapters.vectorstores.faiss_store import FAISSVectorStore
from .models import Segment, TopicBlock
from .qa import answer
from .topic_segmentation import topics_from_segments
from ..config import TOPIC_MODEL, VECTOR_DIMENSION


class Orchestrator:
    """Orchestrates the workflow between different adapters."""

    def __init__(self, openai_api_key: Optional[str] = None):
        # Initialize transcript factory
        self.transcript_factory = TranscriptFactory(openai_api_key=openai_api_key)

        # Initialize embeddings provider
        self.embeddings = OpenAIEmbeddings(api_key=openai_api_key)

        # Initialize vector store
        self.vector_store = FAISSVectorStore(dimension=VECTOR_DIMENSION)

        # Store config for topic analysis
        self.cfg = type("Config", (), {"topic_model": TOPIC_MODEL})()

    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL."""
        parsed = urlparse(url)
        if parsed.hostname in ["youtube.com", "www.youtube.com"]:
            if parsed.path == "/watch":
                return parse_qs(parsed.query)["v"][0]
        elif parsed.hostname in ["youtu.be", "www.youtu.be"]:
            return parsed.path[1:]
        raise ValueError(f"Invalid YouTube URL: {url}")

    def _get_topics_cache_path(self, video_id: str) -> str:
        """Get path for cached topics file."""
        return os.path.join(
            self.transcript_factory.cache_dir, f"{video_id}_topics.json"
        )

    def _load_cached_topics(self, video_id: str) -> Optional[List[TopicBlock]]:
        """Load cached topics if they exist."""
        cache_path = self._get_topics_cache_path(video_id)
        if os.path.exists(cache_path):
            print(f"Loading cached topics from {cache_path}")
            with open(cache_path, "r") as f:
                topics_data = json.load(f)
                return [
                    TopicBlock(
                        title=t["title"],
                        start=t["start"],
                        segments=[Segment(**s) for s in t["segments"]],
                    )
                    for t in topics_data
                ]
        return None

    def _save_topics_cache(self, video_id: str, topics: List[TopicBlock]):
        """Save topics to cache."""
        cache_path = self._get_topics_cache_path(video_id)
        topics_data = [
            {
                "title": t.title,
                "start": t.start,
                "segments": [
                    {"text": s.text, "start": s.start, "duration": s.duration}
                    for s in t.segments
                ],
            }
            for t in topics
        ]
        with open(cache_path, "w") as f:
            json.dump(topics_data, f)
        print(f"Cached topics to {cache_path}")

    def process_video(self, video_url: str) -> Dict[str, Any]:
        """Process a video: get transcript, create embeddings, and store in vector store."""
        try:
            # Extract video ID from URL
            video_id = self._extract_video_id(video_url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")

            # Get transcript (TranscriptFactory handles merging and caching)
            print(f"Getting transcript for video {video_id}")
            segments = self.transcript_factory.get_transcript(video_id)
            if not segments:
                raise ValueError("Failed to get transcript")

            # Create embeddings for segments
            print(f"Creating embeddings for {len(segments)} chunks")
            embeddings = self.embeddings.get_embeddings([s.text for s in segments])

            # Prepare metadata for vector store
            metadata = [
                {
                    "video_id": video_id,
                    "text": s.text,
                    "start": s.start,
                    "duration": s.duration,
                    "chunk_index": i,
                }
                for i, s in enumerate(segments)
            ]

            # Add to vector store (FAISSStore will handle caching)
            print(f"Adding vectors to store for video {video_id}")
            self.vector_store.add_vectors(np.array(embeddings), metadata)

            # Analyze topics in the background
            self.analyze_topics(video_id)

            return {
                "video_id": video_id,
                "num_segments": len(segments),
                "segments": [
                    {"text": s.text, "start": s.start, "duration": s.duration}
                    for s in segments
                ],
            }

        except Exception as e:
            print(f"Error processing video: {str(e)}")
            raise

    def analyze_topics(self, video_id: str) -> List[TopicBlock]:
        """Analyze topics in the video transcript."""
        try:
            print(f"\n=== Starting topic analysis for video {video_id} ===")

            # Check cache first
            print("Checking for cached topics...")
            cache_path = self._get_topics_cache_path(video_id)
            print(f"Cache path: {cache_path}")

            cached_topics = self._load_cached_topics(video_id)
            if cached_topics:
                print("\nLoaded topics from cache:")
                for topic in cached_topics:
                    print(f"- {topic.title} (starts at {topic.start:.1f}s)")
                return cached_topics

            # Get transcript
            print("\nNo cached topics found. Getting transcript...")
            segments = self.transcript_factory.get_transcript(video_id)
            if not segments:
                print("Error: No transcript found")
                raise ValueError("No transcript found")
            print(f"Got {len(segments)} segments from transcript")

            # Extract topics
            print(f"\nAnalyzing topics for video {video_id}")
            try:
                print(f"Using topic model: {self.cfg.topic_model}")
                topics = topics_from_segments(segments, self.cfg)

                if not topics:
                    print("Warning: topics_from_segments returned empty list")
                    raise ValueError("No topics were extracted")

                # Print extracted topics
                print("\nExtracted topics:")
                for topic in topics:
                    print(f"- {topic.title} (starts at {topic.start:.1f}s)")

                # Cache the results
                print("\nSaving topics to cache...")
                self._save_topics_cache(video_id, topics)
                print("Topics saved to cache for future use")

                return topics

            except Exception as e:
                print(f"\nFailed to extract topics: {str(e)}")
                print("Stack trace:", e.__class__.__name__)
                import traceback

                print(traceback.format_exc())

                # Return a single topic covering the entire video as fallback
                print("\nCreating fallback topic...")
                fallback_topic = TopicBlock(
                    title="Full Video Content",
                    start=segments[0].start,
                    segments=segments,
                )
                print("Using fallback topic: Full Video Content")
                return [fallback_topic]

        except Exception as e:
            print(f"Error in analyze_topics: {str(e)}")
            print("Stack trace:", e.__class__.__name__)
            import traceback

            print(traceback.format_exc())
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
