#!/bin/bash

echo "🚀 啟動 AI 會議助手後端..."

# 確認在 backend 目錄
if [ ! -f "main.py" ]; then
    echo "❌ 錯誤：請在 backend 目錄執行此腳本"
    echo "   當前目錄：$(pwd)"
    echo "   請執行：cd backend && ./start.sh"
    exit 1
fi

# 檢查虛擬環境
if [ ! -d "venv" ]; then
    echo "📦 創建 Python 虛擬環境..."
    python3 -m venv venv
fi

# 啟動虛擬環境
echo "🔧 啟動虛擬環境..."
source venv/bin/activate

# 確認在虛擬環境中
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ 虛擬環境已啟動：$(basename $VIRTUAL_ENV)"
else
    echo "❌ 虛擬環境啟動失敗"
    exit 1
fi

# 檢查並安裝依賴
if [ ! -f "venv/.deps_installed" ]; then
    echo "📦 安裝 Python 依賴套件..."
    pip install --upgrade pip
    pip install -r requirements.txt
    touch venv/.deps_installed
fi

# 檢查 .env 文件
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，創建範例文件..."
    cat > .env << 'EOF'
# 開發用設定 - 請填入真實的 API Keys
HF_TOKEN=hf_your_huggingface_token_here
OPENROUTER_API_KEY=sk-or-your_openrouter_key_here

# 基本設定
DEVICE=cpu
COMPUTE_TYPE=float32
WHISPER_MODEL_SIZE=base
DEFAULT_LANGUAGE=zh
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info
TEMP_DIR=/tmp/ai_meeting_tool
UPLOAD_DIR=/tmp/audio_uploads
EOF
    echo "✅ 已創建 .env 文件，請編輯並填入你的 API Keys"
    echo "   HF_TOKEN: https://huggingface.co/settings/tokens"
    echo "   OPENROUTER_API_KEY: https://openrouter.ai/keys"
    echo ""
    echo "🔄 填入 API Keys 後重新執行：./start.sh"
    exit 0
fi

# 載入環境變數並啟動
echo "🎯 載入環境變數並啟動後端服務..."
echo "📡 後端 API: http://localhost:8000"
echo "📚 API 文檔: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服務"
echo "----------------------------------------"

# 載入 .env 並啟動
set -a
source .env
set +a
python main.py