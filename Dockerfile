FROM python:3.11-slim

# Install system dependencies (Tesseract OCR)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy complete project
COPY . .

# Launch FastAPI web server on Render assigned PORT
CMD uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT