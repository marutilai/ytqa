"""
# Test YouTube captions
pytest ytqa/tests/test_transcripts.py::TestTranscriptFactory::test_get_transcript_real_video -v -s

# Test Whisper fallback
pytest ytqa/tests/test_transcripts.py::TestTranscriptFactory::test_get_transcript_real_video_no_captions -v -s

# Test Whisper directly
pytest ytqa/tests/test_transcripts.py::TestWhisperTranscriptProvider::test_get_transcript_real_video -v -s
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from typing import List
from dotenv import load_dotenv

from ytqa.adapters.transcripts.factory import TranscriptFactory
from ytqa.adapters.transcripts.youtube import YouTubeTranscriptProvider
from ytqa.adapters.transcripts.whisper import WhisperTranscriptProvider
from ytqa.core.models import Segment

# Load environment variables
load_dotenv()


class TestYouTubeTranscriptProvider(unittest.TestCase):
    def setUp(self):
        self.provider = YouTubeTranscriptProvider(language="en")

    @patch("youtube_transcript_api.YouTubeTranscriptApi.get_transcript")
    def test_get_transcript_success(self, mock_get_transcript):
        # Mock successful transcript response
        mock_get_transcript.return_value = [
            {"text": "Hello", "start": 0.0, "duration": 1.0},
            {"text": "World", "start": 1.0, "duration": 1.0},
        ]

        result = self.provider.get_transcript("test_video_id")

        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], Segment)
        self.assertEqual(result[0].text, "Hello")
        self.assertEqual(result[0].start, 0.0)
        self.assertEqual(result[0].duration, 1.0)

    @patch("youtube_transcript_api.YouTubeTranscriptApi.get_transcript")
    def test_get_transcript_not_found(self, mock_get_transcript):
        from youtube_transcript_api import NoTranscriptFound

        # Create a proper NoTranscriptFound exception with required arguments
        mock_get_transcript.side_effect = NoTranscriptFound(
            video_id="test_video_id",
            requested_language_codes=["en"],
            transcript_data={},
        )

        with self.assertRaises(ValueError):
            self.provider.get_transcript("test_video_id")

    def test_get_transcript_real_video(self):
        """Test with a real YouTube video that has captions."""
        video_id = "iDulhoQ2pro"
        result = self.provider.get_transcript(video_id)

        # Basic validation
        self.assertGreater(
            len(result), 0, "Should have at least one transcript segment"
        )
        self.assertIsInstance(result[0], Segment)

        # Print first few segments for inspection
        print("\nFirst few transcript segments from YouTube captions:")
        for i, segment in enumerate(result[:5]):
            print(
                f"{i+1}. [{segment.start:.2f}s - {segment.start + segment.duration:.2f}s] {segment.text}"
            )


class TestWhisperTranscriptProvider(unittest.TestCase):
    def setUp(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.provider = WhisperTranscriptProvider(api_key=api_key)

    @patch("yt_dlp.YoutubeDL")
    @patch("openai.audio.transcriptions.create")
    @patch("openai.OpenAI")
    def test_get_transcript_success(self, mock_openai, mock_transcribe, mock_ydl):
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.audio.transcriptions.create = mock_transcribe

        # Mock audio file path
        mock_ydl.return_value.__enter__.return_value.download.return_value = None

        # Mock Whisper response
        mock_segment = MagicMock()
        mock_segment.text = "Hello"
        mock_segment.start = 0.0
        mock_segment.end = 1.0

        mock_response = MagicMock()
        mock_response.segments = [mock_segment]
        mock_transcribe.return_value = mock_response

        result = self.provider.get_transcript("test_video_id")

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Segment)
        self.assertEqual(result[0].text, "Hello")
        self.assertEqual(result[0].start, 0.0)
        self.assertEqual(result[0].duration, 1.0)

    @patch("openai.api_key", None)
    def test_init_no_api_key(self):
        with self.assertRaises(ValueError):
            WhisperTranscriptProvider()

    def test_get_transcript_real_video(self):
        """Test Whisper transcription on a real YouTube video."""
        video_id = "iDulhoQ2pro"
        result = self.provider.get_transcript(video_id)

        # Basic validation
        self.assertGreater(
            len(result), 0, "Should have at least one transcript segment"
        )
        self.assertIsInstance(result[0], Segment)

        # Print first few segments for inspection
        print("\nFirst few transcript segments from Whisper:")
        for i, segment in enumerate(result[:5]):
            print(
                f"{i+1}. [{segment.start:.2f}s - {segment.start + segment.duration:.2f}s] {segment.text}"
            )


class TestTranscriptFactory(unittest.TestCase):
    def setUp(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.factory = TranscriptFactory(openai_api_key=api_key)

    @patch("ytqa.adapters.transcripts.youtube.YouTubeTranscriptProvider.get_transcript")
    def test_get_transcript_youtube_success(self, mock_youtube):
        # Mock successful YouTube transcript
        mock_youtube.return_value = [Segment(text="Hello", start=0.0, duration=1.0)]

        result = self.factory.get_transcript("test_video_id")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].text, "Hello")
        mock_youtube.assert_called_once_with("test_video_id")

    @patch("ytqa.adapters.transcripts.youtube.YouTubeTranscriptProvider.get_transcript")
    @patch("ytqa.adapters.transcripts.whisper.WhisperTranscriptProvider.get_transcript")
    def test_get_transcript_fallback_to_whisper(self, mock_whisper, mock_youtube):
        # Mock YouTube failure
        mock_youtube.side_effect = ValueError("No transcript available")

        # Mock successful Whisper transcript
        mock_whisper.return_value = [Segment(text="Hello", start=0.0, duration=1.0)]

        result = self.factory.get_transcript("test_video_id")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].text, "Hello")
        mock_youtube.assert_called_once_with("test_video_id")
        mock_whisper.assert_called_once_with("test_video_id")

    def test_get_transcript_real_video(self):
        """Test with a real YouTube video that has captions."""
        video_id = "iDulhoQ2pro"
        result = self.factory.get_transcript(video_id)

        # Basic validation
        self.assertGreater(
            len(result), 0, "Should have at least one transcript segment"
        )
        self.assertIsInstance(result[0], Segment)

        # Print first few segments for inspection
        print("\nFirst few transcript segments from YouTube captions:")
        for i, segment in enumerate(result[:5]):
            print(
                f"{i+1}. [{segment.start:.2f}s - {segment.start + segment.duration:.2f}s] {segment.text}"
            )

    def test_get_transcript_real_video_no_captions(self):
        """Test with a real YouTube video that has no captions, forcing Whisper fallback."""
        # Use a video ID that we know has no captions
        video_id = "iDulhoQ2pro"  # We'll force Whisper by patching YouTube to fail
        with patch(
            "ytqa.adapters.transcripts.youtube.YouTubeTranscriptProvider.get_transcript"
        ) as mock_youtube:
            # Force YouTube to fail
            mock_youtube.side_effect = ValueError("No transcript available")

            result = self.factory.get_transcript(video_id)

            # Basic validation
            self.assertGreater(
                len(result), 0, "Should have at least one transcript segment"
            )
            self.assertIsInstance(result[0], Segment)

            # Print first few segments for inspection
            print("\nFirst few transcript segments from Whisper (fallback):")
            for i, segment in enumerate(result[:5]):
                print(
                    f"{i+1}. [{segment.start:.2f}s - {segment.start + segment.duration:.2f}s] {segment.text}"
                )


if __name__ == "__main__":
    unittest.main()
