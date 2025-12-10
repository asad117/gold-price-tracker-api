# FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# WORKDIR /app

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# COPY . .

# # Install Chromium for Playwright
# RUN playwright install chromium

# EXPOSE 8080

# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]



# Use slim Python base
FROM python:3.11-slim

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg wget \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxcomposite1 libxdamage1 libxrandr2 libgbm1 libgtk-3-0 \
    libxss1 libasound2 fonts-liberation lsb-release procps \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

# Install Playwright browsers + deps (important)
RUN python -m playwright install --with-deps chromium

# Copy project files
COPY . /app

ENV PORT=10000

# Default command (Render will override start commands)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
