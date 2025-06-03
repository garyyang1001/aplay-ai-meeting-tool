#!/bin/bash

# AI Meeting Tool - 快速啟動腳本
# 自動設置環境並啟動服務

set -e  # 遇到錯誤立即退出

echo "🚀 AI Meeting Tool - 快速啟動腳本"
echo "=================================="

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 檢查 Python 版本
check_python() {
    echo -e "${BLUE}檢查 Python 版本...${NC}"
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        echo -e "${GREEN}✅ Python 版本: $PYTHON_VERSION${NC}"
        
        # 檢查版本是否 >= 3.8
        MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [[ $MAJOR -lt 3 || ($MAJOR -eq 3 && $MINOR -lt 8) ]]; then
            echo -e "${RED}❌ 需要 Python 3.8 或更高版本${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ 未找到 Python3，請先安裝 Python${NC}"
        exit 1
    fi
}

# 檢查系統依賴
check_system_deps() {
    echo -e "${BLUE}檢查系統依賴...${NC}"
    
    # 檢查 ffmpeg
    if ! command -v ffmpeg &> /dev/null; then
        echo -e "${YELLOW}⚠️  未找到 ffmpeg，正在嘗試安裝...${NC}"
        
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            if command -v brew &> /dev/null; then
                brew install ffmpeg
            else
                echo -e "${RED}❌ 請先安裝 Homebrew 或手動安裝 ffmpeg${NC}"
                exit 1
            fi
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux
            if command -v apt &> /dev/null; then
                sudo apt update && sudo apt install -y ffmpeg libsndfile1
            elif command -v yum &> /dev/null; then
                sudo yum install -y ffmpeg libsndfile
            else
                echo -e "${RED}❌ 請手動安裝 ffmpeg 和 libsndfile${NC}"
                exit 1
            fi
        fi
    else
        echo -e "${GREEN}✅ ffmpeg 已安裝${NC}"
    fi
}

# 設置 Python 虛擬環境
setup_venv() {
    echo -e "${BLUE}設置 Python 虛擬環境...${NC}"
    
    if [[ ! -d "backend/venv" ]]; then
        echo "創建虛擬環境..."
        cd backend
        python3 -m venv venv
        cd ..
    fi
    
    echo "啟動虛擬環境..."
    source backend/venv/bin/activate
    
    echo -e "${GREEN}✅ 虛擬環境已啟動${NC}"
}

# 安裝 Python 依賴
install_python_deps() {
    echo -e "${BLUE}安裝 Python 依賴套件...${NC}"
    
    cd backend
    source venv/bin/activate
    
    # 升級 pip
    pip install --upgrade pip
    
    # 安裝依賴
    pip install -r requirements.txt
    
    echo -e "${GREEN}✅ Python 依賴安裝完成${NC}"
    cd ..
}

# 檢查環境變數
check_env_vars() {
    echo -e "${BLUE}檢查環境變數...${NC}"
    
    ENV_FILE="backend/.env"
    
    if [[ ! -f "$ENV_FILE" ]]; then
        echo "創建 .env 檔案..."
        cp backend/.env.example "$ENV_FILE"
    fi
    
    # 檢查必要變數
    source "$ENV_FILE" 2>/dev/null || true
    
    if [[ -z "$HF_TOKEN" ]]; then
        echo -e "${YELLOW}⚠️  請設定 HuggingFace Token${NC}"
        echo "1. 訪問 https://huggingface.co/settings/tokens"
        echo "2. 創建新的 Read token"
        echo "3. 接受模型使用條款："
        echo "   - https://huggingface.co/pyannote/speaker-diarization-3.1"
        echo "   - https://huggingface.co/pyannote/segmentation-3.0"
        echo ""
        read -p "請輸入您的 HuggingFace Token: " HF_TOKEN
        
        # 更新 .env 檔案
        if grep -q "HF_TOKEN=" "$ENV_FILE"; then
            sed -i.bak "s/HF_TOKEN=.*/HF_TOKEN=$HF_TOKEN/" "$ENV_FILE"
        else
            echo "HF_TOKEN=$HF_TOKEN" >> "$ENV_FILE"
        fi
    else
        echo -e "${GREEN}✅ HuggingFace Token 已設定${NC}"
    fi
    
    if [[ -z "$OPENROUTER_API_KEY" ]]; then
        echo -e "${YELLOW}⚠️  請設定 OpenRouter API Key${NC}"
        echo "1. 訪問 https://openrouter.ai"
        echo "2. 註冊並取得免費 API Key"
        echo ""
        read -p "請輸入您的 OpenRouter API Key: " OPENROUTER_API_KEY
        
        # 更新 .env 檔案
        if grep -q "OPENROUTER_API_KEY=" "$ENV_FILE"; then
            sed -i.bak "s/OPENROUTER_API_KEY=.*/OPENROUTER_API_KEY=$OPENROUTER_API_KEY/" "$ENV_FILE"
        else
            echo "OPENROUTER_API_KEY=$OPENROUTER_API_KEY" >> "$ENV_FILE"
        fi
    else
        echo -e "${GREEN}✅ OpenRouter API Key 已設定${NC}"
    fi
}

# 安裝前端依賴
setup_frontend() {
    echo -e "${BLUE}設置前端環境...${NC}"
    
    if command -v npm &> /dev/null; then
        echo "安裝前端依賴..."
        npm install
        echo -e "${GREEN}✅ 前端依賴安裝完成${NC}"
    else
        echo -e "${YELLOW}⚠️  未找到 npm，跳過前端設置${NC}"
    fi
}

# 啟動服務
start_services() {
    echo -e "${BLUE}啟動服務...${NC}"
    
    # 創建啟動腳本
    cat > start_backend.sh << 'EOF'
#!/bin/bash
cd backend
source venv/bin/activate
source .env
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python main.py
EOF
    
    chmod +x start_backend.sh
    
    cat > start_frontend.sh << 'EOF'
#!/bin/bash
if command -v npm &> /dev/null; then
    npm run dev
else
    echo "前端需要 Node.js 和 npm"
    echo "請先安裝 Node.js: https://nodejs.org/"
fi
EOF
    
    chmod +x start_frontend.sh
    
    echo -e "${GREEN}✅ 啟動腳本已創建${NC}"
    echo ""
    echo -e "${YELLOW}現在可以啟動服務：${NC}"
    echo "後端：./start_backend.sh"
    echo "前端：./start_frontend.sh"
    echo ""
    echo -e "${BLUE}或者手動啟動：${NC}"
    echo "後端：cd backend && source venv/bin/activate && python main.py"
    echo "前端：npm run dev"
}

# 主要流程
main() {
    echo -e "${BLUE}開始設置 AI Meeting Tool...${NC}"
    echo ""
    
    check_python
    check_system_deps
    setup_venv
    install_python_deps
    check_env_vars
    setup_frontend
    start_services
    
    echo ""
    echo -e "${GREEN}🎉 設置完成！${NC}"
    echo ""
    echo -e "${YELLOW}下一步：${NC}"
    echo "1. 在一個終端運行：./start_backend.sh"
    echo "2. 在另一個終端運行：./start_frontend.sh"
    echo "3. 開啟瀏覽器訪問：http://localhost:3000"
    echo ""
    echo -e "${BLUE}API 文檔：http://localhost:8000/docs${NC}"
    echo ""
    echo -e "${YELLOW}故障排除：${NC}"
    echo "- 如果遇到 GPU 記憶體不足，設置環境變數：export DEVICE=cpu"
    echo "- 如果模型下載慢，可以設置：export HF_HUB_CACHE=/path/to/cache"
    echo "- 詳細日誌：查看終端輸出"
}

# 檢查是否在正確目錄
if [[ ! -f "package.json" || ! -d "backend" ]]; then
    echo -e "${RED}❌ 請在專案根目錄運行此腳本${NC}"
    exit 1
fi

# 運行主流程
main
