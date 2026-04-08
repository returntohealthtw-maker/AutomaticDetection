FROM python:3.12-slim

WORKDIR /app

# 安裝系統依賴（psycopg2 需要）
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p reports

EXPOSE 8080

# PORT 環境變數由 Railway 注入，預設 8080
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
