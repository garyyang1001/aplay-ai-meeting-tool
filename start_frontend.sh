#!/bin/bash

# AI 會議工具前端啟動腳本
# 啟動前端開發服務器

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 顯示歡迎信息
show_banner() {
    clear
    echo -e "${BLUE}"
    cat << "EOF"
    ╔══════════════════════════════════════════════════╗
    ║                🌐 前端服務啟動                    ║
    ║              AI 會議助手 v2.0                     ║
    ╚══════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# 檢查環境
check_environment() {
    log_info "檢查前端環境..."
    
    # 檢查 Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js 未安裝，請先安裝 Node.js v18.0.0 或更高版本"
        exit 1
    fi
    
    local node_version=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$node_version" -lt 18 ]; then
        log_error "Node.js 版本過舊 ($(node -v))，需要 v18.0.0 或更高版本"
        exit 1
    fi
    
    log_success "Node.js 版本: $(node -v)"
    
    # 檢查 npm
    if ! command -v npm &> /dev/null; then
        log_error "npm 未安裝"
        exit 1
    fi
    
    log_success "npm 版本: $(npm -v)"
    
    # 檢查項目文件
    if [ ! -f "package.json" ]; then
        log_error "package.json 不存在，請確認在正確的專案目錄中"
        exit 1
    fi
    
    if [ ! -f "index.html" ]; then
        log_error "index.html 不存在"
        exit 1
    fi
    
    log_success "專案文件檢查通過"
}

# 安裝依賴
install_dependencies() {
    log_info "檢查並安裝依賴..."
    
    if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules" ]; then
        log_info "安裝 npm 依賴..."
        npm install
        log_success "依賴安裝完成"
    else
        log_success "依賴已是最新"
    fi
}

# 檢查環境配置
check_configuration() {
    log_info "檢查環境配置..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            log_warning ".env 文件不存在，從 .env.example 複製"
            cp .env.example .env
            log_warning "請編輯 .env 文件設置必要的環境變數"
        else
            log_error ".env.example 文件不存在"
            exit 1
        fi
    fi
    
    # 檢查關鍵配置
    local missing_configs=()
    
    if ! grep -q "VITE_OPENROUTER_API_KEY=" .env || grep -q "your_api_key_here" .env; then
        missing_configs+=("VITE_OPENROUTER_API_KEY")
    fi
    
    if ! grep -q "VITE_FIREBASE_API_KEY=" .env; then
        missing_configs+=("VITE_FIREBASE_API_KEY")
    fi
    
    if [ ${#missing_configs[@]} -gt 0 ]; then
        log_warning "以下配置項目需要設置："
        for config in "${missing_configs[@]}"; do
            echo "  - $config"
        done
        echo ""
        log_warning "系統將以有限功能模式運行"
    else
        log_success "環境配置檢查通過"
    fi
}

# 檢查端口可用性
check_port() {
    local port=${1:-5173}
    
    if lsof -i :$port >/dev/null 2>&1; then
        log_warning "端口 $port 已被佔用"
        
        # 嘗試找到佔用進程
        local pid=$(lsof -ti :$port)
        if [ -n "$pid" ]; then
            local process=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
            log_info "佔用進程: $process (PID: $pid)"
            
            read -p "是否終止佔用進程並繼續? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                kill -9 $pid 2>/dev/null || true
                sleep 2
                log_success "進程已終止"
            else
                log_error "無法啟動前端服務"
                exit 1
            fi
        fi
    fi
}

# 顯示服務信息
show_service_info() {
    echo ""
    log_success "前端服務啟動成功！"
    echo ""
    echo "📱 前端服務："
    echo "  🌐 本地地址: http://localhost:5173"
    echo "  🌐 網路地址: http://$(hostname -I | awk '{print $1}' 2>/dev/null || echo 'localhost'):5173"
    echo ""
    echo "🔧 開發工具："
    echo "  📊 開發者工具: F12"
    echo "  🔄 熱重載: 已啟用"
    echo "  📝 錯誤日誌: 瀏覽器控制台"
    echo ""
    echo "🚀 下一步操作："
    echo "  1. 訪問上方網址打開應用"
    echo "  2. 確保 Mac Mini 服務也在運行 (cd mac-processor && ./start.sh)"
    echo "  3. 設置 Cloudflare Tunnel (cd mac-processor && ./tunnel.sh quick)"
    echo "  4. 開始使用 AI 會議工具！"
    echo ""
    echo "💡 提示："
    echo "  - 使用 Ctrl+C 停止服務"
    echo "  - 修改代碼後會自動重新載入"
    echo "  - 查看 README.md 獲取更多說明"
    echo ""
}

# 主函數
main() {
    show_banner
    
    check_environment
    install_dependencies
    check_configuration
    check_port 5173
    
    echo ""
    log_info "啟動前端開發服務器..."
    
    # 顯示服務信息
    show_service_info
    
    # 啟動開發服務器
    npm run dev
}

# 錯誤處理
trap 'log_error "前端服務啟動過程中發生錯誤"; exit 1' ERR

# 執行主函數
main "$@"
