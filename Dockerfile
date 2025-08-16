# ============================================
# 第一階段：建構階段
# ============================================
FROM mcr.microsoft.com/playwright/python:v1.54.0-noble AS builder

# 安裝必要系統依賴
RUN apt-get update && apt-get install -y \
    curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安裝 UV（使用官方安裝腳本）
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# 設定工作目錄
WORKDIR /app

# 複製依賴檔案
COPY pyproject.toml uv.lock ./

# 安裝 Python 依賴（僅生產依賴）
RUN uv sync --frozen --no-dev

# ============================================
# 第二階段：執行階段 (runtime)
# 使用 Playwright 官方鏡像 (含瀏覽器與 driver)
# ============================================
FROM mcr.microsoft.com/playwright/python:v1.54.0-noble AS runtime

# 設定環境變數
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Taipei \
    PATH="/app/.venv/bin:$PATH"

# 設定時區
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 建立 appuser
RUN useradd -m -s /bin/bash appuser

WORKDIR /app

# 複製 venv（很重要，否則 runtime 會缺依賴）
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# 複製程式碼
COPY --chown=appuser:appuser . .

# 建立可寫目錄並調整權限
RUN mkdir -p /app/screenshots /app/logs /app/tmp /app/scripts \
    && chmod -R 755 /app \
    && chmod -R 777 /app/screenshots /app/logs /app/tmp

USER appuser

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/app/src'); from config import config_manager; config_manager.load_config()" || exit 1

# 預設命令：直接用 venv 裡的 python
CMD ["python", "main.py", "--schedule"]

# ============================================
# Metadata
# ============================================
LABEL maintainer="震旦HR自動打卡系統" \
      version="3.2" \
      description="使用 Playwright 官方鏡像的安全多階段建構容器 (最終優化版)" \
      python.version="3.11" \
      playwright.version="v1.54.0" \
      base.image="mcr.microsoft.com/playwright/python:v1.54.0-noble" \
      security.level="high"