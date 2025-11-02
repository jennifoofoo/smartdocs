FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose Chainlit port
EXPOSE 8000

# Default command (expects Ollama at OLLAMA_BASE_URL)
CMD ["chainlit", "run", "app.py", "--port", "8000", "--host", "0.0.0.0"]

