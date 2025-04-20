# YTQA - YouTube Video Question Answering

A Python library for question-answering on YouTube videos using transcripts and AI.

## Features

- Automatic transcript retrieval from YouTube videos
- Fallback to Whisper transcription when captions aren't available
- Vector-based semantic search for relevant context
- AI-powered question answering using retrieved context
- CLI interface for easy interaction

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ytqa.git
cd ytqa

# Install with Poetry
poetry install
```

## Configuration

The following environment variables are required:

```bash
OPENAI_API_KEY=your_openai_api_key  # Required for Whisper and embeddings
```

You can also create a `.env` file in the project root.

## Usage

Basic usage from the command line:

```bash
# Fetch and cache a video transcript
ytqa fetch "https://www.youtube.com/watch?v=VIDEO_ID"

# Ask a question about the video
ytqa ask VIDEO_ID "When does X happen in the video?"
```

## Development

```bash
# Run tests
poetry run pytest

# Format code
poetry run black ytqa tests
poetry run isort ytqa tests
```

## License

MIT License - see LICENSE file for details. 