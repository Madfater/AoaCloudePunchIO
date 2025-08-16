# 多階段建構 Dockerfile for 自動打卡系統
# 使用 UV 作為 Python 套件管理器

# ============================================
# 第一階段：建構階段
# ============================================
FROM python:3.11-slim AS builder

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安裝 UV (使用官方安裝腳本)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# 設定工作目錄
WORKDIR /app

# 複製 UV 配置檔案
COPY pyproject.toml uv.lock ./

# 安裝 Python 依賴（包含開發依賴，用於建構）
RUN uv sync --frozen --no-dev

# ============================================
# 第二階段：執行階段
# ============================================
FROM python:3.11-slim AS runtime

# 設定環境變數
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CACHE_DIR=/tmp/uv-cache \
    PATH="/app/.venv/bin:$PATH" \
    UV_NO_CACHE=1

# 安裝系統依賴和 Playwright 瀏覽器依賴
RUN apt-get update && apt-get install -y \
    # 基本工具
    curl \
    wget \
    gnupg \
    ca-certificates \
    # Playwright 瀏覽器依賴
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    # 其他工具
    cron \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# 設定時區為台北
ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 建立非 root 使用者（使用可配置的 UID/GID）
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd --gid ${GROUP_ID} appuser && \
    useradd --uid ${USER_ID} --gid appuser --shell /bin/bash --create-home appuser

# 設定工作目錄
WORKDIR /app

# 安裝 UV（執行階段也需要）
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# 複製應用程式代碼
COPY --chown=appuser:appuser . .

# 複製權限檢查腳本
COPY --chown=appuser:appuser scripts/check_permissions.sh /app/check_permissions.sh
RUN chmod +x /app/check_permissions.sh

# 從建構階段複製虛擬環境並設定正確的擁有者
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# 安裝 Playwright 系統依賴（作為 root）
RUN /root/.local/bin/uv run playwright install-deps chromium

# 建立必要的目錄並設定權限
RUN mkdir -p /app/screenshots /app/logs && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    chmod -R 777 /app/screenshots /app/logs

# 切換到非 root 使用者
USER appuser

# 為 appuser 安裝 UV
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/appuser/.local/bin:$PATH"

# 作為 appuser 安裝 Playwright 瀏覽器
RUN uv run playwright install chromium


# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/app/src'); from config import config_manager; config_manager.load_config()" || exit 1

# 暴露埠（如果需要的話）
# EXPOSE 8080

# 預設命令（可以被覆蓋）
CMD ["uv", "run", "python", "main.py", "--schedule"]

# ============================================
# 建構說明和標籤
# ============================================
LABEL maintainer="震旦HR自動打卡系統" \
      version="1.0" \
      description="使用 Playwright 和 UV 的自動打卡容器" \
      python.version="3.11" \
      uv.version="latest"

# 建構指令範例:
# docker build -t aoacloude-punch:latest .
# docker run -d --name punch-scheduler --env-file .env aoacloude-punch:latest

# 開發模式:
# docker run -it --rm -v $(pwd):/app aoacloude-punch:latest bash