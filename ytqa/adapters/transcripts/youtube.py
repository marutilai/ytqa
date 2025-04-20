from typing import List
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)

from .base import TranscriptProvider
from ...core.models import Segment


class YouTubeTranscriptProvider(TranscriptProvider):
    """Provider for native YouTube captions."""

    def __init__(self, language: str = "en", cache_dir: str = None):
        super().__init__(cache_dir)
        self.language = language

    def get_transcript(self, video_id: str) -> List[Segment]:
        # Check for cached transcript first
        cached_segments = self._load_cached_transcript(video_id)
        if cached_segments is not None:
            return cached_segments

        try:
            # Get transcript from YouTube
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id, languages=[self.language]
            )
            segments = [
                Segment(
                    text=entry["text"], start=entry["start"], duration=entry["duration"]
                )
                for entry in transcript
            ]

            # Cache the transcript
            self._save_cached_transcript(video_id, segments)
            return segments

        except (TranscriptsDisabled, NoTranscriptFound) as e:
            raise ValueError(f"No YouTube transcript available: {str(e)}")
