# Use Node.js LTS version
FROM node:20-slim as builder

# Set working directory
WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy frontend source code
COPY frontend/ ./

# Copy cookies file for API requests
COPY cookies.txt /app/cookies.txt

# Build the application
RUN npm run build

# Production stage
FROM node:20-slim

WORKDIR /app

# Copy built assets from builder stage
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/cookies.txt ./cookies.txt

# Install only production dependencies
RUN npm install --production

# Expose port 3000
EXPOSE 3000

# Start the production server
CMD ["npm", "run", "start"] 