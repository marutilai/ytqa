import os
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import shutil
from dotenv import load_dotenv

from ytqa.adapters.transcripts.whisper import WhisperTranscriptProvider
from ytqa.core.models import Segment


class TestPipedIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        load_dotenv()
        cls.api_key = os.getenv("OPENAI_API_KEY")
        if not cls.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        # Create a test-specific cache directory
        cls.test_cache_dir = tempfile.mkdtemp(prefix="ytqa_test_cache_")
        cls.provider = WhisperTranscriptProvider(
            cache_dir=cls.test_cache_dir, api_key=cls.api_key
        )
        cls.test_video_id = "jNQXAC9IVRw"  # "Me at the zoo" - First YouTube video

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        # Remove the test cache directory and all its contents
        if hasattr(cls, "test_cache_dir") and os.path.exists(cls.test_cache_dir):
            shutil.rmtree(cls.test_cache_dir)

    @patch("requests.get")
    def test_piped_download(self, mock_get):
        """Test audio download using Piped API."""
        # Mock successful healthcheck
        mock_healthcheck = MagicMock()
        mock_healthcheck.status_code = 200

        # Mock successful streams response
        mock_streams = MagicMock()
        mock_streams.status_code = 200
        mock_streams.json.return_value = {
            "audioStreams": [
                {
                    "url": "https://example.com/audio.mp3",
                    "format": "M4A",
                    "bitrate": 128000,
                }
            ]
        }

        # Mock successful audio download
        mock_audio = MagicMock()
        mock_audio.status_code = 200
        mock_audio.iter_content.return_value = [b"test audio data"]

        # Configure mock to return different responses
        mock_get.side_effect = [mock_healthcheck, mock_streams, mock_audio]

        # Mock FFmpeg subprocess call
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            audio_path = self.provider._download_audio(self.test_video_id)

            self.assertIsNotNone(audio_path)
            self.assertTrue(audio_path.endswith(".wav"))
            self.assertTrue(os.path.dirname(audio_path).startswith(self.test_cache_dir))

    @patch("requests.get")
    @patch("openai.audio.transcriptions.create")
    def test_whisper_transcription(self, mock_transcribe, mock_get):
        """Test Whisper transcription with Piped-downloaded audio."""
        # Mock Piped API responses
        mock_healthcheck = MagicMock()
        mock_healthcheck.status_code = 200

        mock_streams = MagicMock()
        mock_streams.status_code = 200
        mock_streams.json.return_value = {
            "audioStreams": [
                {
                    "url": "https://example.com/audio.mp3",
                    "format": "M4A",
                    "bitrate": 128000,
                }
            ]
        }

        mock_audio = MagicMock()
        mock_audio.status_code = 200
        mock_audio.iter_content.return_value = [b"test audio data"]

        mock_get.side_effect = [mock_healthcheck, mock_streams, mock_audio]

        # Create test audio files in the cache directory
        mp3_path = os.path.join(self.test_cache_dir, f"{self.test_video_id}.mp3")
        wav_path = os.path.join(self.test_cache_dir, f"{self.test_video_id}.wav")
        transcript_path = os.path.join(
            self.test_cache_dir, f"{self.test_video_id}.json"
        )

        # Create test MP3 file
        with open(mp3_path, "wb") as f:
            f.write(b"test audio data")

        # Create test WAV file
        with open(wav_path, "wb") as f:
            f.write(b"test wav data")

        # Mock FFmpeg duration check
        ffprobe_output = MagicMock()
        ffprobe_output.stdout = "60.0\n"
        ffprobe_output.returncode = 0

        # Create a proper OpenAI API response mock
        mock_segment = MagicMock()
        mock_segment.text = "Hello, this is a test"
        mock_segment.start = 0.0
        mock_segment.end = 1.0

        mock_response = MagicMock()
        mock_response.segments = [mock_segment]
        mock_transcribe.return_value = mock_response

        # Mock FFmpeg subprocess calls
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = ffprobe_output

            segments = self.provider.get_transcript(self.test_video_id)

            self.assertIsInstance(segments, list)
            self.assertTrue(all(isinstance(s, Segment) for s in segments))

            if segments:  # Only check if we got segments
                first_segment = segments[0]
                self.assertIsInstance(first_segment.text, str)
                self.assertIsInstance(first_segment.start, (int, float))
                self.assertIsInstance(first_segment.duration, (int, float))

            # Verify the mock was called correctly
            mock_transcribe.assert_called_once()

            # Verify the transcript was cached
            self.assertTrue(
                os.path.exists(transcript_path), "Transcript cache file should exist"
            )
            self.assertTrue(os.path.exists(mp3_path), "MP3 file should still exist")

            # Read and verify the cached transcript
            with open(transcript_path, "r") as f:
                import json

                cached_transcript = json.load(f)
                self.assertIsInstance(cached_transcript, list)
                self.assertTrue(len(cached_transcript) > 0)

    @unittest.skip("Skip real API test - use only for manual testing")
    def test_real_transcription(self):
        """Test full pipeline with a real video (integration test)."""
        try:
            segments = self.provider.get_transcript(self.test_video_id)
            self.assertIsInstance(segments, list)
            self.assertTrue(all(isinstance(s, Segment) for s in segments))

            if segments:  # Print first few segments for inspection
                print("\nFirst few transcript segments:")
                for i, segment in enumerate(segments[:3], 1):
                    print(
                        f"\n{i}. [{segment.start:.2f}s - {segment.start + segment.duration:.2f}s]"
                    )
                    print(f"   {segment.text}")
        except Exception as e:
            self.fail(f"Failed to get transcript: {str(e)}")


if __name__ == "__main__":
    unittest.main()
