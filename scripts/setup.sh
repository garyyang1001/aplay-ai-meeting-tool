#!/bin/bash

# AI Meeting Tool 安裝腳本
# 自動設定 WhisperX 環境

set -e  # 錯誤時退出

echo "🚀 AI Meeting Tool 安裝腳本"
echo "==========================="

# 檢查作業系統
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    echo "📱 檢測到 macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    echo "🐧 檢測到 Linux"
else
    echo "❌ 不支援的作業系統: $OSTYPE"
    exit 1
fi

# 檢查 Python 版本
echo "\n🐍 檢查 Python 版本..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "✅ Python 版本: $PYTHON_VERSION"
    
    # 檢查版本是否符合要求
    if [[ "$PYTHON_VERSION" < "3.8" ]]; then
        echo "❌ Python 版本過舊，需要 3.8 或更新版本"
        exit 1
    fi
else
    echo "❌ 未找到 Python 3"
    exit 1
fi

# 安裝系統依賴
echo "\n📦 安裝系統依賴..."
if [[ "$OS" == "macos" ]]; then
    # macOS 使用 Homebrew
    if ! command -v brew &> /dev/null; then
        echo "❌ 未找到 Homebrew，請先安裝: https://brew.sh"
        exit 1
    fi
    
    echo "🍺 使用 Homebrew 安裝依賴..."
    brew update
    brew install redis ffmpeg
    
elif [[ "$OS" == "linux" ]]; then
    # Linux 使用 apt
    echo "📋 使用 apt 安裝依賴..."
    sudo apt update
    sudo apt install -y python3-pip python3-venv redis-server ffmpeg git curl
fi

# 建立虛擬環境
echo "\n🏠 建立 Python 虛擬環境..."
if [[ -d "whisperx-env" ]]; then
    echo "⚠️  虛擬環境已存在，將覆蓋"
    rm -rf whisperx-env
fi

python3 -m venv whisperx-env
source whisperx-env/bin/activate

echo "✅ 虛擬環境建立完成"

# 升級 pip
echo "\n📈 升級 pip..."
pip install --upgrade pip

# 安裝 PyTorch (根據系統選擇)
echo "\n🔥 安裝 PyTorch..."
if [[ "$OS" == "macos" ]]; then
    # macOS: 支援 MPS (Apple Silicon GPU)
    pip install torch torchaudio
elif [[ "$OS" == "linux" ]]; then
    # Linux: 優先安裝 CUDA 版本
    if command -v nvidia-smi &> /dev/null; then
        echo "🎯 檢測到 NVIDIA GPU，安裝 CUDA 版本"
        pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
    else
        echo "💻 安裝 CPU 版本"
        pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
    fi
fi

# 安裝 WhisperX 和其他依賴
echo "\n🎙️  安裝 WhisperX..."
cd backend
pip install -r requirements.txt

# 安裝 WhisperX
echo "📥 安裝 WhisperX 最新版本..."
pip install git+https://github.com/m-bain/whisperx.git

# 設定環境變數
echo "\n⚙️  設定環境變數..."
if [[ ! -f ".env" ]]; then
    cp .env.example .env
    echo "✅ 建立 .env 檔案"
else
    echo "⚠️  .env 檔案已存在"
fi

# 提示設定 API 金鑰
echo "\n🔑 請設定必要的 API 金鑰:"
echo "\n1. HuggingFace Token (說話者辨識功能):"
echo "   - 前往: https://huggingface.co/settings/tokens"
echo "   - 建立 Read token"
echo "   - 接受模型條款:"
echo "     * https://huggingface.co/pyannote/speaker-diarization-3.1"
echo "     * https://huggingface.co/pyannote/segmentation-3.0"
echo
echo "2. OpenRouter API Key (AI 分析功能):"
echo "   - 前往: https://openrouter.ai"
echo "   - 註冊並取得免費 API 金鑰"
echo
echo "請在 backend/.env 檔案中設定這些金鑰"

# 啟動 Redis
echo "\n🗄️  啟動 Redis..."
if [[ "$OS" == "macos" ]]; then
    brew services start redis
    echo "✅ Redis 已啟動 (macOS service)"
elif [[ "$OS" == "linux" ]]; then
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
    echo "✅ Redis 已啟動 (systemd service)"
fi

# 測試安裝
echo "\n🧪 測試 WhisperX 安裝..."
if python test_whisperx.py; then
    echo "\n🎉 WhisperX 安裝測試通過！"
else
    echo "\n⚠️  WhisperX 安裝測試有問題，請檢查上述輸出"
fi

# 安裝前端依賴 (如果存在 package.json)
echo "\n🌐 安裝前端依賴..."
cd ..
if [[ -f "package.json" ]]; then
    if command -v npm &> /dev/null; then
        npm install
        echo "✅ 前端依賴安裝完成"
    else
        echo "⚠️  未找到 npm，請手動安裝前端依賴"
    fi
else
    echo "⚠️  未找到 package.json"
fi

# 建立啟動腳本
echo "\n📜 建立啟動腳本..."
cat > start_backend.sh << 'EOF'
#!/bin/bash
echo "🚀 啟動 AI Meeting Tool 後端..."
cd backend
source whisperx-env/bin/activate
python -m uvicorn main:app --reload --port 8000
EOF

chmod +x start_backend.sh

cat > start_frontend.sh << 'EOF'
#!/bin/bash
echo "🌐 啟動 AI Meeting Tool 前端..."
npm run dev
EOF

chmod +x start_frontend.sh

echo "✅ 啟動腳本建立完成"

# 完成訊息
echo "\n🎊 安裝完成！"
echo "==========="
echo
echo "下一步:"
echo "1. 編輯 backend/.env 設定 API 金鑰"
echo "2. 執行 ./start_backend.sh 啟動後端"
echo "3. 另開終端執行 ./start_frontend.sh 啟動前端"
echo "4. 開啟瀏覽器訪問 http://localhost:3000"
echo
echo "🔧 疑難排解:"
echo "- 執行 backend/test_whisperx.py 測試 WhisperX"
echo "- 查看 docs/deployment.md 了解更多部署選項"
echo "- 有問題請開啟 GitHub Issue"
echo
echo "🎉 享受你的 AI 會議助手！"