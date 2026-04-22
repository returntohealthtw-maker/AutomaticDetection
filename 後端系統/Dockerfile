FROM python:3.12-slim
LABEL maintainer="AutomaticDetection" version="1.0"

WORKDIR /app

# 安裝系統依賴（psycopg2 需要）
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p reports && \
    echo "=== static-app contents ===" && \
    ls -la static-app/ 2>/dev/null || echo "WARNING: static-app not found"

EXPOSE 8080

# PORT 環境變數由 Railway 注入，預設 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
