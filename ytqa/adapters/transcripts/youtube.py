"""
DEPRECATED: This module is kept for legacy purposes only.
The application now uses the Piped API provider (piped.py) for better reliability and privacy.
Do not use this module for new development.
"""

from typing import List
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    NoTranscriptAvailable,
)

from .base import TranscriptProvider
from ...core.models import Segment


class YouTubeTranscriptProvider(TranscriptProvider):
    """
    DEPRECATED: Legacy YouTube transcript provider.
    This provider is kept for reference but is no longer actively used.
    Use PipedTranscriptProvider instead for better reliability and privacy.
    """

    def __init__(self, language: str = "en", cache_dir: str = None):
        super().__init__(cache_dir)
        self.language = language

    def get_transcript(self, video_id: str) -> List[Segment]:
        """
        DEPRECATED: Get transcript from YouTube's transcript API.
        This method is kept for reference but is no longer actively used.
        Use PipedTranscriptProvider.get_transcript() instead.
        """
        # Check for cached transcript first
        cached_segments = self._load_cached_transcript(video_id)
        if cached_segments is not None:
            print(f"Using cached transcript for video {video_id}")
            return cached_segments

        print(
            f"No cached transcript found for video {video_id}, fetching from YouTube..."
        )
        try:
            # Get transcript from YouTube
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            try:
                transcript = transcript_list.find_transcript([self.language])
            except NoTranscriptFound:
                print(f"No {self.language} transcript found, trying auto-translate...")
                transcript = transcript_list.find_transcript(
                    transcript_list.transcript_data.keys()
                ).translate(self.language)

            transcript_data = transcript.fetch()

            # Convert to segments
            segments = []
            for item in transcript_data:
                segment = Segment(
                    text=item["text"],
                    start=float(item["start"]),
                    duration=float(item["duration"]),
                )
                segments.append(segment)

            # Cache the transcript
            self._save_cached_transcript(video_id, segments)

            return segments

        except (NoTranscriptFound, TranscriptsDisabled, NoTranscriptAvailable) as e:
            raise ValueError(f"Failed to get transcript: {str(e)}")
