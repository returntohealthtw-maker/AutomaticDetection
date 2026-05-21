FROM python:3.12-slim
LABEL maintainer="AutomaticDetection" version="1.0"

WORKDIR /app

# 安裝系統依賴
#   gcc/libpq-dev：psycopg2 編譯
#   fonts-noto-cjk：Playwright 啟動的 Chromium 渲染你 React App 時需要中文字型
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安裝 Playwright 與 Chromium（含執行所需的系統依賴）
# 注意：playwright install --with-deps chromium 會自動裝 chromium + 必要的 .so
RUN playwright install --with-deps chromium

COPY . .

RUN mkdir -p reports && \
    echo "=== static-app contents ===" && \
    ls -la static-app/ 2>/dev/null || echo "WARNING: static-app not found"

EXPOSE 8080

# PORT 環境變數由 Railway 注入，預設 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
