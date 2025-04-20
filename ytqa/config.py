"""Configuration settings for the YTQA application."""

import os
import tempfile

# Transcript settings
TRANSCRIPT_CHUNK_DURATION = (
    60.0  # Target duration for merged transcript chunks in seconds
)
TRANSCRIPT_MAX_FILE_SIZE = (
    25 * 1024 * 1024
)  # Maximum file size for Whisper API in bytes

# Model settings
TOPIC_MODEL = "gpt-4.1-nano"  # Model for topic extraction
EMBEDDING_MODEL = "text-embedding-3-large"  # Model for embeddings
QA_MODEL = "gpt-4.1-nano"  # Model for question answering

# Vector store settings
VECTOR_DIMENSION = 3072  # Dimension for text-embedding-3-large

# Topic extraction settings
MAX_TOPIC_DURATION = 60 * 10  # Maximum duration for a topic in seconds
MIN_TOPIC_DURATION = 60 * 2  # Minimum duration for a topic in seconds

# Cache settings
CACHE_DIR = os.path.join(tempfile.gettempdir(), "ytqa_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
