# AI Meeting Tool Backend Dockerfile
# 基於 WhisperX 的會議助手後端

# 使用官方 Python 映像
FROM python:3.10-slim

# 設定維護者
LABEL maintainer="AI Meeting Tool Team"
LABEL description="WhisperX-based meeting assistant backend"

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libgomp1 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 設定 Python 環境變數
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# 複製需求檔案
COPY backend/requirements.txt .

# 安裝 Python 依賴
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 安裝 WhisperX
RUN pip install git+https://github.com/m-bain/whisperx.git

# 複製應用程式碼
COPY backend/ .

# 建立必要目錄
RUN mkdir -p /tmp/audio_uploads /var/log/whisperx

# 設定檔案權限
RUN chmod +x test_whisperx.py

# 建立非 root 使用者
RUN useradd -r -s /bin/bash -u 1001 whisperx && \
    chown -R whisperx:whisperx /app /tmp/audio_uploads /var/log/whisperx

# 切換使用者
USER whisperx

# 設定環境變數
ENV UPLOAD_DIR=/tmp/audio_uploads
ENV LOG_DIR=/var/log/whisperx
ENV DEVICE=auto
ENV BATCH_SIZE=16
ENV COMPUTE_TYPE=float16

# 健康檢查
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 啟動命令
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]