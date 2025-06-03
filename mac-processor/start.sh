#!/bin/bash

# Mac Mini 音頻處理服務啟動腳本
# 使用方法：./start.sh [dev|prod]

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日誌函數
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 檢查運行模式
MODE=${1:-dev}
if [[ "$MODE" != "dev" && "$MODE" != "prod" ]]; then
    log_error "無效的運行模式: $MODE"
    echo "使用方法: $0 [dev|prod]"
    exit 1
fi

log_info "啟動 Mac Mini 處理服務 (${MODE} 模式)"

# 檢查是否在 mac-processor 目錄中
if [[ ! -f "main.py" || ! -f "requirements.txt" ]]; then
    log_error "請在 mac-processor 目錄中運行此腳本"
    exit 1
fi

# 檢查 Python 版本
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 未安裝"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
log_info "檢測到 Python 版本: $PYTHON_VERSION"

# 檢查並創建虛擬環境
if [[ ! -d "venv" ]]; then
    log_info "創建 Python 虛擬環境..."
    python3 -m venv venv
    log_success "虛擬環境創建成功"
fi

# 啟動虛擬環境
log_info "啟動虛擬環境..."
source venv/bin/activate

# 升級 pip
log_info "升級 pip..."
pip install --upgrade pip

# 安裝依賴
log_info "安裝依賴套件..."
pip install -r requirements.txt

# 檢查環境配置
if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        log_warning ".env 文件不存在，從 .env.example 複製"
        cp .env.example .env
        log_warning "請編輯 .env 文件設置必要的環境變數"
    else
        log_error ".env.example 文件不存在"
        exit 1
    fi
fi

# 載入環境變數
if [[ -f ".env" ]]; then
    log_info "載入環境變數..."
    set -a
    source .env
    set +a
fi

# 檢查必要的環境變數
check_env_var() {
    local var_name=$1
    local var_value=${!var_name}
    
    if [[ -z "$var_value" || "$var_value" == *"your_"* || "$var_value" == *"_here"* ]]; then
        log_error "請在 .env 文件中設置 $var_name"
        return 1
    fi
    return 0
}

log_info "檢查環境配置..."
ENV_CHECK_FAILED=false

if ! check_env_var "HF_TOKEN"; then
    ENV_CHECK_FAILED=true
fi

if [[ "$ENV_CHECK_FAILED" == "true" ]]; then
    log_error "環境配置檢查失敗，請修正 .env 文件"
    exit 1
fi

# 檢查 Hugging Face 模型權限
log_info "檢查 Hugging Face 模型權限..."
python3 -c "
import os
from huggingface_hub import HfApi
try:
    api = HfApi(token=os.getenv('HF_TOKEN'))
    # 檢查模型訪問權限
    models = [
        'pyannote/speaker-diarization-3.1',
        'pyannote/segmentation-3.0'
    ]
    for model in models:
        try:
            api.model_info(model)
            print(f'✓ {model} 權限正常')
        except Exception as e:
            print(f'✗ {model} 權限錯誤: {e}')
            exit(1)
except Exception as e:
    print(f'HF Token 驗證失敗: {e}')
    exit(1)
"

if [[ $? -ne 0 ]]; then
    log_error "Hugging Face 權限檢查失敗"
    log_info "請確認："
    echo "  1. HF_TOKEN 是否正確"
    echo "  2. 已接受模型使用條款："
    echo "     - https://huggingface.co/pyannote/speaker-diarization-3.1"
    echo "     - https://huggingface.co/pyannote/segmentation-3.0"
    exit 1
fi

log_success "Hugging Face 配置正確"

# 檢查 GPU 支援
log_info "檢查 GPU 支援..."
python3 -c "
import torch
if torch.cuda.is_available():
    print(f'✓ GPU 可用: {torch.cuda.get_device_name(0)}')
    print(f'✓ CUDA 版本: {torch.version.cuda}')
else:
    print('✓ 使用 CPU 模式')
"

# 創建必要的目錄
log_info "創建必要目錄..."
mkdir -p logs temp

# 清理舊的臨時檔案
log_info "清理臨時檔案..."
rm -rf temp/*.wav temp/*.mp3 2>/dev/null || true

# 設置運行參數
if [[ "$MODE" == "dev" ]]; then
    HOST=${HOST:-"0.0.0.0"}
    PORT=${PORT:-8000}
    RELOAD_FLAG="--reload"
    LOG_LEVEL="debug"
else
    HOST=${HOST:-"0.0.0.0"}
    PORT=${PORT:-8000}
    RELOAD_FLAG=""
    LOG_LEVEL="info"
fi

# 檢查端口是否被佔用
if lsof -i :$PORT >/dev/null 2>&1; then
    log_warning "端口 $PORT 已被佔用"
    read -p "是否要終止佔用端口的進程? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "終止佔用端口 $PORT 的進程..."
        lsof -ti :$PORT | xargs kill -9 2>/dev/null || true
        sleep 2
    else
        log_error "無法啟動服務，端口被佔用"
        exit 1
    fi
fi

# 啟動服務
log_info "啟動音頻處理服務..."
log_info "服務地址: http://$HOST:$PORT"
log_info "模式: $MODE"

# 根據模式啟動服務
if [[ "$MODE" == "dev" ]]; then
    log_info "開發模式 - 支援熱重載"
    python3 main.py
else
    log_info "生產模式"
    # 使用 gunicorn 或 uvicorn 生產模式
    uvicorn main:app \
        --host "$HOST" \
        --port "$PORT" \
        --workers 1 \
        --log-level "$LOG_LEVEL" \
        --access-log \
        --loop uvloop
fi
