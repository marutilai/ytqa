from typing import List, Dict, Any
import openai
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def format_chunks_for_context(chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved chunks into a context string for the LLM."""
    context = []
    for chunk in chunks:
        # Format time as MM:SS
        start_min = int(chunk["start"] // 60)
        start_sec = int(chunk["start"] % 60)
        time_str = f"{start_min:02d}:{start_sec:02d}"

        context.append(f"[{time_str}] {chunk['text']}")

    return "\n\n".join(context)


def answer(
    query: str, chunks: List[Dict[str, Any]], model: str = "gpt-3.5-turbo"
) -> str:
    """
    Generate an answer to a user query based on retrieved transcript chunks.

    Args:
        query: The user's question
        chunks: List of relevant transcript chunks from FAISS store
        model: OpenAI model to use for completion

    Returns:
        str: Generated answer with relevant timestamps
    """
    if not chunks:
        return "I couldn't find any relevant information to answer your question."

    # Format chunks into context
    context = format_chunks_for_context(chunks)

    # Prepare the prompt
    system_prompt = """You are a helpful assistant that answers questions about YouTube videos based on their transcripts.
When answering questions:
1. Use only the information provided in the transcript chunks
2. If you're not sure about something, say so
3. Include relevant timestamps [MM:SS] when referencing specific parts
4. Keep your answers concise and to the point
5. If the question can't be answered with the given context, say so"""

    user_prompt = f"""Here are some relevant parts of the video transcript:

{context}

Question: {query}

Please provide a helpful answer based on the transcript above."""

    # Make the API call
    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Sorry, I encountered an error while generating the answer: {str(e)}"
