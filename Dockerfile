FROM python:3.11-slim

# Install system dependencies (Tesseract OCR)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# RAM Optimizations for 512MB free tier limits
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1

# Install CPU-only PyTorch first (slams memory usage from ~450MB down to ~120MB)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install Python packages
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy complete project
COPY . .

# Launch FastAPI web server on Render assigned PORT
CMD uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT