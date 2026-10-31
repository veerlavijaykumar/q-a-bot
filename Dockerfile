# ==========================================
# Stage 1: Build the React frontend
# ==========================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Python Backend runtime
# ==========================================
FROM python:3.12-slim

# Install system dependencies (Tesseract OCR for scanned documents, OpenMP for FAISS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Ensure data and vector store directories exist
RUN mkdir -p data vector_store

# Copy application source code and pre-indexed vector store
COPY src/ ./src/
COPY data/ ./data/
COPY vector_store/ ./vector_store/

# Copy built frontend production bundle from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Cloud providers (Render, Cloud Run, Railway) pass the port via $PORT
ENV PORT=8000
EXPOSE 8000

# Start unified FastAPI server
CMD ["sh", "-c", "uvicorn src.server:app --host 0.0.0.0 --port ${PORT}"]
