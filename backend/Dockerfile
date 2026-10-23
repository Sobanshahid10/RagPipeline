FROM python:3.11-slim

WORKDIR /app

# Install system build dependencies and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade "pip>=26.2" "setuptools>=83.0.0" \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Privacy processing is required before any document text reaches a provider.
RUN python -m spacy download en_core_web_sm
RUN useradd --create-home --uid 10001 rag && mkdir -p /app/storage/uploads && chown -R rag:rag /app
USER rag

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
