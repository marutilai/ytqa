"""Configuration settings for the application."""

import os
import tempfile

# Transcript settings
TRANSCRIPT_CHUNK_DURATION = (
    60.0  # Target duration for merged transcript chunks in seconds
)
TRANSCRIPT_MAX_FILE_SIZE = (
    25 * 1024 * 1024
)  # Maximum file size for Whisper API in bytes

# Cache settings
CACHE_DIR = os.path.join(tempfile.gettempdir(), "ytqa_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
