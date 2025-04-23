# YouTube QA

AI-powered application that processes YouTube videos to provide transcripts, extract topics, and answer questions about the content.

## Prerequisites

- Docker and Docker Compose
- OpenAI API key

## Quick Start

1. **Setup**
   ```bash
   # Clone and enter directory
   git clone https://github.com/marutilai/ytqa.git
   cd ytqa

   # Create and configure environment
   cp .env.example .env
   # Add your OPENAI_API_KEY to .env
   ```

2. **Development**
   ```bash
   # Run locally
   docker compose up --build
   # Visit http://localhost:3000
   ```

3. **Production**
   ```bash
   # Deploy with SSL
   docker compose -f docker-compose.prod.yml up --build -d
   
   # Get SSL certificate
   docker compose -f docker-compose.prod.yml run --rm certbot certonly \
     --webroot --webroot-path /var/www/certbot/ \
     -d your-domain.com
   ```

## Architecture

- Frontend: React + Vite + TypeScript
- Backend: Python + FastAPI
- AI: OpenAI API for embeddings and topic extraction

