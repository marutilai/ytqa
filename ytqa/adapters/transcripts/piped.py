import os
import tempfile
import subprocess
import time
from typing import List, Optional, Tuple
import requests
from urllib3.exceptions import InsecureRequestWarning
import json

from .base import TranscriptProvider
from ...core.models import Segment
from ...config import PIPED_INSTANCES, PIPED_TIMEOUT, PIPED_MAX_RETRIES

# Suppress only the single InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class PipedTranscriptProvider(TranscriptProvider):
    """Provider for downloading audio using Piped API."""

    def __init__(self, cache_dir: str = None):
        super().__init__(cache_dir)
        self.instances = PIPED_INSTANCES
        self.timeout = PIPED_TIMEOUT
        self.max_retries = PIPED_MAX_RETRIES

    def _make_request(
        self, url: str, stream: bool = False
    ) -> Tuple[bool, requests.Response]:
        """Make a request with retries."""
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url,
                    timeout=self.timeout,
                    verify=False,  # Some instances use self-signed certs
                    stream=stream,
                )
                response.raise_for_status()
                return True, response
            except Exception as e:
                print(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(1 * (attempt + 1))  # Exponential backoff
                continue
        return False, None

    def _get_working_instance(self) -> Optional[str]:
        """Find a working Piped instance."""
        for instance in self.instances:
            success, _ = self._make_request(f"{instance}/healthcheck")
            if success:
                print(f"Using Piped instance: {instance}")
                return instance
            print(f"Instance {instance} is not available")
        return None

    def _download_audio(self, video_id: str) -> Optional[str]:
        """Download audio using Piped API."""
        # Check if we already have the WAV file
        wav_path = self._get_cached_path(video_id, ".wav")
        if os.path.exists(wav_path):
            print(f"Using cached WAV file: {wav_path}")
            return wav_path

        # Check if we already have the MP3 file
        mp3_path = self._get_cached_path(video_id, ".mp3")
        if os.path.exists(mp3_path):
            print(f"Using cached MP3 file: {mp3_path}")
            # Convert MP3 to WAV
            print("Converting cached MP3 to WAV...")
            ffmpeg_cmd = [
                "ffmpeg",
                "-i",
                mp3_path,
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                wav_path,
            ]
            subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
            return wav_path

        # Try each instance until we find one that works
        for instance in self.instances:
            try:
                # Get stream information
                print(f"Trying instance {instance} for video {video_id}")
                success, response = self._make_request(f"{instance}/streams/{video_id}")
                if not success:
                    continue

                data = response.json()
                audio_streams = data.get("audioStreams", [])
                if not audio_streams:
                    print(f"No audio streams found on {instance}")
                    continue

                # Sort by bitrate and prefer m4a/mp4 format
                audio_streams.sort(
                    key=lambda x: (
                        x.get("format", "").lower() in ["m4a", "mp4"],
                        int(x.get("bitrate", 0)),
                    ),
                    reverse=True,
                )
                best_audio = audio_streams[0]
                audio_url = best_audio["url"]

                # Download the audio file
                print(f"Downloading audio from {audio_url}")
                success, response = self._make_request(audio_url, stream=True)
                if not success:
                    continue

                with tempfile.NamedTemporaryFile(
                    suffix=".mp3", delete=False
                ) as temp_file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            temp_file.write(chunk)
                    temp_path = temp_file.name

                # Cache the MP3 file
                os.rename(temp_path, mp3_path)
                print(f"Cached MP3 file: {mp3_path}")

                # Convert to WAV using FFmpeg
                print("Converting to WAV with FFmpeg...")
                ffmpeg_cmd = [
                    "ffmpeg",
                    "-i",
                    mp3_path,
                    "-acodec",
                    "pcm_s16le",
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    wav_path,
                ]
                subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
                print(f"Cached WAV file: {wav_path}")

                return wav_path

            except Exception as e:
                print(f"Failed with instance {instance}: {str(e)}")
                continue

        # If we get here, all instances failed
        print("All Piped instances failed")
        # Clean up any partial downloads
        for path in [mp3_path, wav_path]:
            if os.path.exists(path):
                os.remove(path)
        raise RuntimeError("Failed to download audio from any Piped instance")

    def get_transcript(self, video_id: str) -> List[Segment]:
        """Get transcript using Whisper API."""
        # This provider only handles audio download
        # The actual transcription should be done by WhisperTranscriptProvider
        raise NotImplementedError(
            "PipedTranscriptProvider only handles audio download. "
            "Use WhisperTranscriptProvider for transcription."
        )
