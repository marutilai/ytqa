from typing import List, Optional
import os
import json
import tempfile

from .piped import PipedTranscriptProvider
from .whisper import WhisperTranscriptProvider
from .base import TranscriptProvider
from ...core.models import Segment
from ...config import CACHE_DIR


class TranscriptProvider:
    """Base class for transcript providers."""

    def __init__(self, cache_dir: str = None):
        self.cache_dir = (
            cache_dir or CACHE_DIR or os.path.join(tempfile.gettempdir(), "ytqa_cache")
        )
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cached_path(self, video_id: str, suffix: str) -> str:
        """Get path for cached file with given suffix."""
        return os.path.join(self.cache_dir, f"{video_id}{suffix}")

    def _load_cached_transcript(self, video_id: str) -> List[Segment]:
        """Load cached transcript if it exists."""
        transcript_path = self._get_cached_path(video_id, ".json")
        if os.path.exists(transcript_path):
            print(f"Using cached transcript: {transcript_path}")
            with open(transcript_path, "r") as f:
                segments_data = json.load(f)
                return [Segment(**seg) for seg in segments_data]
        return None

    def _save_cached_transcript(self, video_id: str, segments: List[Segment]):
        """Save transcript to cache."""
        transcript_path = self._get_cached_path(video_id, ".json")
        segments_data = [
            {"text": seg.text, "start": seg.start, "duration": seg.duration}
            for seg in segments
        ]
        with open(transcript_path, "w") as f:
            json.dump(segments_data, f)
        print(f"Cached transcript: {transcript_path}")


class TranscriptFactory:
    """Factory for managing transcript providers with fallback logic."""

    def __init__(self, openai_api_key: Optional[str] = None, language: str = "en"):
        print(f"Initializing TranscriptFactory with cache_dir: {CACHE_DIR}")
        self.piped_provider = PipedTranscriptProvider(cache_dir=CACHE_DIR)
        self.whisper_provider = WhisperTranscriptProvider(
            api_key=openai_api_key, cache_dir=CACHE_DIR
        )
        self.cache_dir = CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cached_path(self, video_id: str) -> str:
        """Get path for cached merged transcript."""
        return os.path.join(self.cache_dir, f"{video_id}_merged.json")

    def _load_cached_transcript(self, video_id: str) -> Optional[List[Segment]]:
        """Load cached merged transcript if it exists."""
        cache_path = self._get_cached_path(video_id)
        if os.path.exists(cache_path):
            print(f"Loading cached merged transcript from {cache_path}")
            with open(cache_path, "r") as f:
                segments_data = json.load(f)
                return [Segment(**seg) for seg in segments_data]
        return None

    def _save_cached_transcript(self, video_id: str, chunks: List[Segment]):
        """Save merged transcript to cache."""
        cache_path = self._get_cached_path(video_id)
        segments_data = [
            {"text": chunk.text, "start": chunk.start, "duration": chunk.duration}
            for chunk in chunks
        ]
        with open(cache_path, "w") as f:
            json.dump(segments_data, f)
        print(f"Cached merged transcript to {cache_path}")

    def _merge_segments(
        self, segments: List[Segment], target_duration: float = 60.0
    ) -> List[Segment]:
        """Merge segments into chunks of approximately target duration."""
        if not segments:
            return []

        chunks = []
        current_chunk = []
        current_duration = 0.0
        current_start = segments[0].start

        for segment in segments:
            if current_duration + segment.duration > target_duration and current_chunk:
                # Create a new chunk
                chunks.append(
                    Segment(
                        text=" ".join(seg.text for seg in current_chunk),
                        start=current_start,
                        duration=current_duration,
                    )
                )
                current_chunk = []
                current_duration = 0.0
                current_start = segment.start

            current_chunk.append(segment)
            current_duration += segment.duration

        # Add the last chunk if there are remaining segments
        if current_chunk:
            chunks.append(
                Segment(
                    text=" ".join(seg.text for seg in current_chunk),
                    start=current_start,
                    duration=current_duration,
                )
            )

        return chunks

    def get_transcript(self, video_id: str) -> List[Segment]:
        """Get transcript, merge segments, and cache the result."""
        # Try to load cached merged transcript first
        cached_chunks = self._load_cached_transcript(video_id)
        if cached_chunks is not None:
            return cached_chunks

        # If no cached transcript, get it from providers
        try:
            print(f"Attempting to get transcript using Piped for video {video_id}")
            segments = self.piped_provider.get_transcript(video_id)
        except Exception as e:
            print(f"Piped transcript not available, falling back to Whisper: {str(e)}")
            segments = self.whisper_provider.get_transcript(video_id)

        # Merge segments into chunks
        chunks = self._merge_segments(segments)
        print(f"Merged {len(segments)} segments into {len(chunks)} chunks")

        # Cache the merged chunks
        self._save_cached_transcript(video_id, chunks)

        return chunks
