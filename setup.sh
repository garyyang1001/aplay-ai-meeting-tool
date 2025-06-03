#!/bin/bash

# AI 會議工具一鍵設置腳本
# 自動設置前端、Mac Mini 處理服務和 Cloudflare Tunnel

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

log_header() {
    echo -e "${CYAN}===================================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}===================================================${NC}"
}

# 顯示歡迎信息
show_welcome() {
    clear
    echo -e "${CYAN}"
    cat << "EOF"
    ╔══════════════════════════════════════════════════╗
    ║                AI 會議工具                        ║
    ║              一鍵設置腳本 v2.0                     ║
    ║                                                  ║
    ║  🎤 錄音轉錄    🤖 AI 分析    👥 說話者識別       ║
    ║  ☁️  Firebase    🔗 Cloudflare   🖥️  Mac Mini     ║
    ╚══════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    echo ""
    log_info "這個腳本將協助您設置完整的 AI 會議工具"
    echo ""
}

# 檢查系統需求
check_system_requirements() {
    log_header "檢查系統需求"
    
    local requirements_met=true
    
    # 檢查作業系統
    if [[ "$OSTYPE" == "darwin"* ]]; then
        log_success "檢測到 macOS 系統"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_success "檢測到 Linux 系統"
    else
        log_error "不支援的作業系統: $OSTYPE"
        requirements_met=false
    fi
    
    # 檢查必要工具
    local tools=("git" "curl" "node" "npm" "python3")
    
    for tool in "${tools[@]}"; do
        if command -v $tool &> /dev/null; then
            log_success "$tool 已安裝"
        else
            log_error "$tool 未安裝"
            requirements_met=false
        fi
    done
    
    # 檢查 Node.js 版本
    if command -v node &> /dev/null; then
        local node_version=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
        if [ "$node_version" -ge 18 ]; then
            log_success "Node.js 版本符合要求 ($(node -v))"
        else
            log_error "Node.js 版本過舊，需要 v18.0.0 或更高版本"
            requirements_met=false
        fi
    fi
    
    # 檢查 Python 版本
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        log_success "Python 版本: $python_version"
    fi
    
    if [ "$requirements_met" = false ]; then
        log_error "系統需求不符合，請安裝缺失的工具後重新運行"
        exit 1
    fi
    
    log_success "系統需求檢查通過"
    echo ""
}

# 設置前端
setup_frontend() {
    log_header "設置前端環境"
    
    # 安裝依賴
    log_info "安裝前端依賴..."
    npm install
    
    # 設置環境變數
    if [[ ! -f ".env" ]]; then
        log_info "創建前端環境配置..."
        cp .env.example .env
        
        echo ""
        log_warning "請設置以下環境變數："
        echo "1. VITE_OPENROUTER_API_KEY - 從 https://openrouter.ai/ 獲取"
        echo "2. Firebase 相關配置 - 從 Firebase Console 獲取"
        echo "3. VITE_MAC_MINI_URL - Mac Mini Tunnel URL（稍後設置）"
        echo ""
        
        read -p "是否現在打開 .env 文件進行編輯? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} .env
        fi
    else
        log_success "前端環境配置已存在"
    fi
    
    log_success "前端設置完成"
    echo ""
}

# 設置 Mac Mini 處理服務
setup_mac_mini() {
    log_header "設置 Mac Mini 處理服務"
    
    if [[ ! -d "mac-processor" ]]; then
        log_error "mac-processor 目錄不存在"
        return 1
    fi
    
    cd mac-processor
    
    # 設置 Python 虛擬環境
    if [[ ! -d "venv" ]]; then
        log_info "創建 Python 虛擬環境..."
        python3 -m venv venv
    fi
    
    # 啟動虛擬環境
    source venv/bin/activate
    
    # 升級 pip
    log_info "升級 pip..."
    pip install --upgrade pip
    
    # 安裝依賴
    log_info "安裝 Python 依賴..."
    pip install -r requirements.txt
    
    # 設置環境變數
    if [[ ! -f ".env" ]]; then
        log_info "創建 Mac Mini 環境配置..."
        cp .env.example .env
        
        echo ""
        log_warning "請設置 Hugging Face Token："
        echo "1. 訪問 https://huggingface.co/settings/tokens"
        echo "2. 創建新的 token"
        echo "3. 接受模型使用條款："
        echo "   - https://huggingface.co/pyannote/speaker-diarization-3.1"
        echo "   - https://huggingface.co/pyannote/segmentation-3.0"
        echo ""
        
        read -p "請輸入您的 Hugging Face Token: " hf_token
        if [[ -n "$hf_token" ]]; then
            sed -i.bak "s/your_huggingface_token_here/$hf_token/" .env
            log_success "Hugging Face Token 已設置"
        fi
        
        read -p "是否現在打開 .env 文件進行進一步編輯? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} .env
        fi
    else
        log_success "Mac Mini 環境配置已存在"
    fi
    
    # 設置腳本執行權限
    chmod +x start.sh tunnel.sh
    
    cd ..
    log_success "Mac Mini 設置完成"
    echo ""
}

# 設置 Cloudflare Tunnel
setup_cloudflare_tunnel() {
    log_header "設置 Cloudflare Tunnel"
    
    cd mac-processor
    
    # 檢查是否安裝 cloudflared
    if ! command -v cloudflared &> /dev/null; then
        log_info "安裝 cloudflared..."
        ./tunnel.sh install
    else
        log_success "cloudflared 已安裝"
    fi
    
    echo ""
    log_info "Cloudflare Tunnel 設置選項："
    echo "1. 快速模式 - 立即啟動臨時 tunnel（測試用）"
    echo "2. 持久模式 - 設置永久 tunnel（生產用）"
    echo "3. 跳過 - 稍後手動設置"
    echo ""
    
    read -p "請選擇 (1/2/3): " -n 1 -r
    echo
    
    case $REPLY in
        1)
            log_info "設置快速 tunnel..."
            log_warning "這將啟動臨時 tunnel，關閉後 URL 會失效"
            log_info "請先在另一個終端啟動 Mac Mini 服務："
            log_info "  cd mac-processor && ./start.sh"
            echo ""
            read -p "Mac Mini 服務已啟動？按 Enter 繼續..."
            ./tunnel.sh quick
            ;;
        2)
            log_info "設置持久 tunnel..."
            ./tunnel.sh setup
            ;;
        3)
            log_info "跳過 tunnel 設置"
            ;;
        *)
            log_warning "無效選擇，跳過 tunnel 設置"
            ;;
    esac
    
    cd ..
    echo ""
}

# 創建啟動腳本
create_startup_scripts() {
    log_header "創建啟動腳本"
    
    # 創建前端啟動腳本
    cat > start_frontend.sh << 'EOF'
#!/bin/bash
echo "🌐 啟動前端服務..."
npm run dev
EOF
    
    # 創建完整啟動腳本
    cat > start_all.sh << 'EOF'
#!/bin/bash

# 完整啟動腳本
echo "🚀 啟動 AI 會議工具完整服務..."

# 檢查終端程式
if command -v gnome-terminal &> /dev/null; then
    TERMINAL="gnome-terminal --"
elif command -v xterm &> /dev/null; then
    TERMINAL="xterm -e"
elif command -v osascript &> /dev/null; then
    # macOS Terminal
    TERMINAL="osascript -e 'tell app \"Terminal\" to do script'"
else
    echo "❌ 無法檢測到終端程式，請手動啟動服務"
    exit 1
fi

echo "📱 在新終端啟動前端服務..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"' && ./start_frontend.sh"'
else
    $TERMINAL "cd $(pwd) && ./start_frontend.sh; exec bash"
fi

echo "🖥️  在新終端啟動 Mac Mini 服務..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"'/mac-processor && ./start.sh"'
else
    $TERMINAL "cd $(pwd)/mac-processor && ./start.sh; exec bash"
fi

echo "🔗 在新終端啟動 Cloudflare Tunnel..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"'/mac-processor && ./tunnel.sh quick"'
else
    $TERMINAL "cd $(pwd)/mac-processor && ./tunnel.sh quick; exec bash"
fi

echo ""
echo "✅ 所有服務啟動中..."
echo ""
echo "📊 服務狀態："
echo "  - 前端服務: http://localhost:5173"
echo "  - Mac Mini API: http://localhost:8000"
echo "  - Tunnel URL: 請查看 tunnel 終端輸出"
echo ""
echo "💡 使用說明："
echo "  1. 等待所有服務啟動完成"
echo "  2. 複製 Tunnel URL 並更新前端 .env 文件"
echo "  3. 重新載入前端頁面"
echo "  4. 開始使用 AI 會議工具！"
echo ""
EOF
    
    # 設置執行權限
    chmod +x start_frontend.sh start_all.sh
    
    log_success "啟動腳本創建完成"
    echo ""
}

# 顯示設置完成信息
show_completion() {
    log_header "設置完成！"
    
    echo -e "${GREEN}🎉 AI 會議工具設置完成！${NC}"
    echo ""
    echo "📋 下一步操作："
    echo ""
    echo "1️⃣  配置環境變數："
    echo "   - 編輯 .env 文件設置 OpenRouter API Key"
    echo "   - 編輯 mac-processor/.env 設置 Hugging Face Token"
    echo ""
    echo "2️⃣  啟動服務："
    echo "   - 一鍵啟動: ./start_all.sh"
    echo "   - 或分別啟動:"
    echo "     • 前端: ./start_frontend.sh"
    echo "     • Mac Mini: cd mac-processor && ./start.sh"
    echo "     • Tunnel: cd mac-processor && ./tunnel.sh quick"
    echo ""
    echo "3️⃣  設置 Tunnel URL："
    echo "   - 複製 Cloudflare Tunnel 輸出的 URL"
    echo "   - 更新 .env 中的 VITE_MAC_MINI_URL"
    echo ""
    echo "4️⃣  開始使用："
    echo "   - 訪問 http://localhost:5173"
    echo "   - 點擊麥克風開始錄音"
    echo "   - 享受 AI 會議分析！"
    echo ""
    echo "📖 詳細文檔："
    echo "   - README.md - 完整使用指南"
    echo "   - mac-processor/README.md - Mac Mini 服務說明"
    echo ""
    echo "❓ 遇到問題？"
    echo "   - 檢查 .env 文件配置"
    echo "   - 查看服務終端輸出"
    echo "   - 確認網路連接正常"
    echo ""
    
    read -p "是否現在啟動所有服務? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "啟動所有服務..."
        ./start_all.sh
    else
        log_info "您可以稍後運行 ./start_all.sh 來啟動所有服務"
    fi
}

# 主執行流程
main() {
    show_welcome
    check_system_requirements
    setup_frontend
    setup_mac_mini
    setup_cloudflare_tunnel
    create_startup_scripts
    show_completion
}

# 錯誤處理
trap 'log_error "設置過程中發生錯誤，請檢查上面的錯誤信息"; exit 1' ERR

# 執行主函數
main "$@"
