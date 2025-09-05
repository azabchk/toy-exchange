# Use official Python runtime
FROM python:3.11-slim

# set workdir
WORKDIR /app

# install dependencies
COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get remove -y gcc libpq-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# copy app
COPY . .

ENV PYTHONPATH=/app

EXPOSE 8000

# Production command (you can override with docker run)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
