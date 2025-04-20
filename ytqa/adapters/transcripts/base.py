from typing import List
import os
import json
import tempfile

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
