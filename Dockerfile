FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for lxml/Pillow/pdfminer etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
    libxml2-dev libxslt-dev \
    libjpeg-dev zlib1g-dev libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# If you have a requirements.txt at the root
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the app
COPY . .

# Default env (can be overridden by .env / compose)
ENV PORT=8080

# --- Office exports (added by office pack) ---
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    libreoffice-core libreoffice-writer libreoffice-impress libreoffice-calc \
    fonts-dejavu fonts-liberation ghostscript pandoc \
 && rm -rf /var/lib/apt/lists/*
# --- end office exports ---
