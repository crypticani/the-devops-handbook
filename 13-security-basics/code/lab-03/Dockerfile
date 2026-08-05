FROM python:3.12-slim
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# A vendored binary — the way real applications actually acquire dependencies
RUN mkdir -p /app/vendor && \
    echo "#!/bin/sh" > /app/vendor/legacy-tool && \
    echo "echo 'legacy-tool v1.2.3'" >> /app/vendor/legacy-tool && \
    chmod +x /app/vendor/legacy-tool
COPY app/ .
RUN useradd -r -u 10001 appuser && chown -R appuser /app
USER 10001
CMD ["python", "main.py"]
