import os
import tempfile
from typing import List
import math
import subprocess
import shutil
import json

import openai

from .base import TranscriptProvider
from .piped import PipedTranscriptProvider
from ...core.models import Segment
from ...config import (
    TRANSCRIPT_CHUNK_DURATION,
    TRANSCRIPT_MAX_FILE_SIZE,
    CACHE_DIR,
)


class WhisperTranscriptProvider(TranscriptProvider):
    """Fallback provider using OpenAI's Whisper API."""

    def __init__(self, api_key: str = None, cache_dir: str = None):
        super().__init__(cache_dir)
        print(f"WhisperTranscriptProvider initialized with cache_dir: {self.cache_dir}")
        if api_key:
            openai.api_key = api_key
        elif not openai.api_key:
            raise ValueError(
                "OpenAI API key must be provided or set in OPENAI_API_KEY environment variable"
            )
        self.piped_provider = PipedTranscriptProvider(cache_dir=cache_dir)

    def _merge_segments(self, segments: List[Segment]) -> List[Segment]:
        """Merge segments into chunks of approximately target duration."""
        if not segments:
            return segments

        merged_segments = []
        current_text = []
        current_start = segments[0].start
        current_duration = 0.0

        for segment in segments:
            # If adding this segment would exceed target duration and we have some text,
            # create a new merged segment
            if (
                current_duration + segment.duration > TRANSCRIPT_CHUNK_DURATION
                and current_text
                and len(current_text) > 0
            ):
                merged_segments.append(
                    Segment(
                        text=" ".join(current_text),
                        start=current_start,
                        duration=current_duration,
                    )
                )
                current_text = []
                current_start = segment.start
                current_duration = 0.0

            # Add segment to current chunk
            current_text.append(segment.text)
            current_duration += segment.duration

        # Add the last chunk if there's any remaining text
        if current_text:
            merged_segments.append(
                Segment(
                    text=" ".join(current_text),
                    start=current_start,
                    duration=current_duration,
                )
            )

        return merged_segments

    def _split_audio(self, audio_path: str) -> List[str]:
        """Split audio file into chunks if it exceeds max_size (in bytes)."""
        file_size = os.path.getsize(audio_path)
        if file_size <= TRANSCRIPT_MAX_FILE_SIZE:
            return [audio_path]

        # Get audio duration using ffprobe
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip())

        # Calculate number of chunks needed based on file size
        num_chunks = math.ceil(file_size / TRANSCRIPT_MAX_FILE_SIZE)
        chunk_duration = duration / num_chunks

        # Split audio into chunks
        chunks = []
        with tempfile.TemporaryDirectory() as temp_dir:
            for i in range(num_chunks):
                start_time = i * chunk_duration
                chunk_path = os.path.join(temp_dir, f"chunk_{i}.wav")

                cmd = [
                    "ffmpeg",
                    "-i",
                    audio_path,
                    "-ss",
                    str(start_time),
                    "-t",
                    str(chunk_duration),
                    "-acodec",
                    "pcm_s16le",
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    chunk_path,
                ]
                subprocess.run(cmd, capture_output=True, check=True)
                chunks.append(chunk_path)

            # Copy chunks to new temporary files that won't be deleted
            final_chunks = []
            for chunk in chunks:
                final_chunk = tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False
                ).name
                shutil.copy2(chunk, final_chunk)
                final_chunks.append(final_chunk)

            return final_chunks

    def _download_audio(self, video_id: str) -> str:
        """Download video audio using Piped API."""
        return self.piped_provider._download_audio(video_id)

    def get_transcript(self, video_id: str) -> List[Segment]:
        # Check for cached transcript first
        cached_segments = self._load_cached_transcript(video_id)
        if cached_segments is not None:
            print(f"Using cached transcript for video {video_id}")
            return cached_segments

        print(f"No cached transcript found for video {video_id}, processing audio...")
        # If no cached transcript, process the audio
        audio_path = self._download_audio(video_id)
        try:
            # Split audio into chunks if needed
            audio_chunks = self._split_audio(audio_path)
            print(f"Processing {len(audio_chunks)} audio chunk(s)...")

            all_segments = []
            for i, chunk_path in enumerate(audio_chunks):
                try:
                    with open(chunk_path, "rb") as audio:
                        response = openai.audio.transcriptions.create(
                            file=audio,
                            model="whisper-1",
                            response_format="verbose_json",
                            timestamp_granularities=["segment"],
                        )

                    # Get the duration of this chunk using ffprobe
                    cmd = [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "default=noprint_wrappers=1:nokey=1",
                        chunk_path,
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    chunk_duration = float(result.stdout.strip())

                    # Adjust timestamps for each chunk
                    chunk_offset = i * chunk_duration
                    for seg in response.segments:
                        all_segments.append(
                            Segment(
                                text=seg.text,
                                start=seg.start + chunk_offset,
                                duration=seg.end - seg.start,
                            )
                        )
                finally:
                    # Clean up chunk file
                    if os.path.exists(chunk_path):
                        os.remove(chunk_path)

            # Merge segments into approximately 1-minute chunks
            merged_segments = self._merge_segments(all_segments)
            print(
                f"Merged {len(all_segments)} segments into {len(merged_segments)} chunks"
            )

            # Cache the transcript
            self._save_cached_transcript(video_id, merged_segments)
            return merged_segments
        finally:
            # Don't clean up the cached audio file
            pass
