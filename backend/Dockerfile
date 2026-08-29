FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
# Fetches the T-100 extract on first boot if data/raw is empty, then execs
# uvicorn. Fail-soft: a failed download still starts the API.
CMD ["python", "scripts/start.py"]
