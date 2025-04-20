import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import logging
from dotenv import load_dotenv

from ..orchestrator import Orchestrator


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


class SearchRequest(BaseModel):
    query: str
    video_id: Optional[str] = None
    k: Optional[int] = 5


class Segment(BaseModel):
    text: str
    start: float
    duration: float


class ProcessResponse(BaseModel):
    video_id: str
    num_segments: int
    segments: List[Segment]


class SearchResponse(BaseModel):
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


@app.post("/search", response_model=SearchResponse)
async def search_transcript(request: SearchRequest):
    """Search the transcript database and get an answer."""
    try:
        logger.info(f"Searching for: {request.query}")
        if request.video_id:
            logger.info(f"Restricting search to video: {request.video_id}")

        answer = orchestrator.answer_question(
            request.query, video_id=request.video_id, k=request.k
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
