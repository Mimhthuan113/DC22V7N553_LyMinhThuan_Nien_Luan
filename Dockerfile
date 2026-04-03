# Backend: FastAPI
FROM python:3.11-slim

WORKDIR /app

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend + knowledge base (.txt trong data/)
COPY *.py ./
COPY data ./data

# Expose backend port
EXPOSE 8000

# Run FastAPI
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
