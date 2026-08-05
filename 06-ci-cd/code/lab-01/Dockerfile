FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
RUN useradd -r appuser
USER appuser
CMD ["python", "-c", "from src.app import add; print(f'2+3={add(2,3)}')"]
