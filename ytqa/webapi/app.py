import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import logging
from dotenv import load_dotenv

from ..core.orchestrator import Orchestrator
from ..core.models import Segment, TopicBlock, Answer


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="YouTube QA API",
    description="API for processing and searching YouTube video transcripts",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    orchestrator = Orchestrator(openai_api_key=api_key)
    logger.info("Orchestrator initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize orchestrator: {str(e)}")
    raise


# Pydantic models for request/response validation
class ProcessRequest(BaseModel):
    url: HttpUrl


class Message(BaseModel):
    """A chat message with its role and content."""

    role: str  # 'user' or 'assistant'
    content: str


class SearchRequest(BaseModel):
    """Request model for transcript search."""

    query: str
    video_id: Optional[str] = None
    k: int = 5
    conversation_history: Optional[List[Message]] = None


class ProcessResponse(BaseModel):
    video_id: str
    num_segments: int
    segments: List[Segment]


class SearchResponse(BaseModel):
    """Response model for transcript search."""

    answer: str


@app.post("/process", response_model=ProcessResponse)
async def process_video(request: ProcessRequest):
    """Process a YouTube video."""
    try:
        logger.info(f"Processing video: {request.url}")
        result = orchestrator.process_video(str(request.url))
        logger.info(f"Successfully processed video: {result['video_id']}")
        return result
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/topics/{video_id}", response_model=List[TopicBlock])
async def get_video_topics(video_id: str):
    """Get topics for a specific video."""
    try:
        logger.info(f"Getting topics for video: {video_id}")
        topics = orchestrator.analyze_topics(video_id)
        if not topics:
            raise HTTPException(status_code=404, detail="Topics not found")
        logger.info(f"Successfully retrieved {len(topics)} topics")
        return topics
    except Exception as e:
        logger.error(f"Error getting topics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=SearchResponse)
async def search_transcript(request: SearchRequest):
    """Search the transcript database and get an answer."""
    try:
        logger.info(f"Searching for: {request.query}")
        if request.video_id:
            logger.info(f"Restricting search to video: {request.video_id}")

        history = request.conversation_history or []
        logger.info(f"Conversation history length: {len(history)}")

        answer = orchestrator.answer_question(
            request.query,
            video_id=request.video_id,
            k=request.k,
            conversation_history=history,
        )
        logger.info("Successfully generated answer")
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Error searching transcript: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
