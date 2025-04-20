import os
import argparse
from dotenv import load_dotenv

from .orchestrator import Orchestrator


def main():
    # Load environment variables
    load_dotenv()

    # Get OpenAI API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        return

    # Initialize orchestrator
    orchestrator = Orchestrator(openai_api_key=api_key)

    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Process and search YouTube video transcripts"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Process video command
    process_parser = subparsers.add_parser("process", help="Process a YouTube video")
    process_parser.add_argument("url", help="YouTube video URL")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search transcripts")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "--k", type=int, default=5, help="Number of results to return"
    )
    search_parser.add_argument("--video_id", help="Restrict search to a specific video")

    # Get transcript command
    transcript_parser = subparsers.add_parser(
        "transcript", help="Get transcript for a video"
    )
    transcript_parser.add_argument("video_id", help="YouTube video ID")

    # Parse arguments
    args = parser.parse_args()

    if args.command == "process":
        try:
            result = orchestrator.process_video(args.url)
            print(f"\nProcessed video: {result['video_id']}")
            print(f"Number of segments: {result['num_segments']}")
            print("\nFirst 5 segments:")
            for segment in result["segments"]:
                print(f"[{segment['start']:.2f}s] {segment['text']}")
        except Exception as e:
            print(f"Error processing video: {e}")

    elif args.command == "search":
        try:
            print(f"\nSearching for: {args.query}")
            if args.video_id:
                print(f"Restricting search to video: {args.video_id}")

            print("\nSearching for relevant content...")
            answer = orchestrator.answer_question(
                args.query, video_id=args.video_id, k=args.k
            )

            print("\nAnswer:")
            print(answer)
        except Exception as e:
            print(f"Error searching transcripts: {e}")

    elif args.command == "transcript":
        try:
            segments = orchestrator.get_video_transcript(args.video_id)
            print(f"\nTranscript for video {args.video_id}:")
            for segment in segments:
                print(f"[{segment['start']:.2f}s] {segment['text']}")
        except Exception as e:
            print(f"Error getting transcript: {e}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
