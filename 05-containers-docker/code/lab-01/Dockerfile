FROM python:3.12-slim

# Metadata
LABEL maintainer="devops-handbook"

# Set working directory
WORKDIR /app

# Install dependencies first (caching!)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .

# Create non-root user
RUN useradd -r -s /usr/sbin/nologin appuser
USER appuser

# Set environment variables
ENV PORT=5000
ENV APP_VERSION=1.0.0

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

CMD ["python", "app.py"]
