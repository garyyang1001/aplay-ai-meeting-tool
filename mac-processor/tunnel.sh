#!/bin/bash

# Cloudflare Tunnel 設置和啟動腳本
# 用於讓 Mac Mini 服務可以從網路存取

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

# 顯示說明
show_help() {
    echo "Cloudflare Tunnel 管理腳本"
    echo ""
    echo "使用方法:"
    echo "  $0 install    - 安裝 cloudflared"
    echo "  $0 quick      - 快速啟動臨時 tunnel"
    echo "  $0 setup      - 設置持久 tunnel"
    echo "  $0 start      - 啟動 tunnel"
    echo "  $0 stop       - 停止 tunnel"
    echo "  $0 status     - 查看狀態"
    echo ""
}

# 檢查作業系統
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    else
        log_error "不支援的作業系統: $OSTYPE"
        exit 1
    fi
    log_info "檢測到作業系統: $OS"
}

# 安裝 cloudflared
install_cloudflared() {
    log_info "安裝 cloudflared..."
    
    if command -v cloudflared &> /dev/null; then
        log_warning "cloudflared 已安裝，版本: $(cloudflared version)"
        return 0
    fi
    
    case $OS in
        "macos")
            if command -v brew &> /dev/null; then
                log_info "使用 Homebrew 安裝..."
                brew install cloudflared
            else
                log_info "下載 macOS 版本..."
                curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz -o cloudflared.tgz
                tar -xzf cloudflared.tgz
                sudo mv cloudflared /usr/local/bin/
                sudo chmod +x /usr/local/bin/cloudflared
                rm cloudflared.tgz
            fi
            ;;
        "linux")
            log_info "下載 Linux 版本..."
            curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
            sudo mv cloudflared /usr/local/bin/
            sudo chmod +x /usr/local/bin/cloudflared
            ;;
    esac
    
    if command -v cloudflared &> /dev/null; then
        log_success "cloudflared 安裝成功，版本: $(cloudflared version)"
    else
        log_error "cloudflared 安裝失敗"
        exit 1
    fi
}

# 快速啟動臨時 tunnel
quick_tunnel() {
    local port=${1:-8000}
    
    log_info "啟動快速 tunnel (端口 $port)..."
    log_warning "這是臨時 tunnel，關閉後 URL 會失效"
    
    # 檢查本地服務是否運行
    if ! curl -s http://localhost:$port/health > /dev/null; then
        log_error "本地服務 (端口 $port) 未運行"
        log_info "請先啟動 Mac Mini 服務："
        log_info "  cd mac-processor && ./start.sh"
        exit 1
    fi
    
    log_info "本地服務正常運行"
    log_info "正在創建 tunnel..."
    
    # 啟動 tunnel
    cloudflared tunnel --url http://localhost:$port
}

# 設置持久 tunnel
setup_tunnel() {
    log_info "設置持久 Cloudflare Tunnel..."
    
    # 檢查是否已登入
    if [[ ! -f ~/.cloudflared/cert.pem ]]; then
        log_info "首次設置，請先登入 Cloudflare..."
        cloudflared tunnel login
    fi
    
    # 創建 tunnel
    local tunnel_name="ai-meeting-tool"
    
    log_info "創建 tunnel: $tunnel_name"
    if cloudflared tunnel list | grep -q "$tunnel_name"; then
        log_warning "Tunnel '$tunnel_name' 已存在"
    else
        cloudflared tunnel create "$tunnel_name"
    fi
    
    # 創建配置文件
    local config_file="$HOME/.cloudflared/config.yml"
    
    log_info "創建配置文件: $config_file"
    cat > "$config_file" << EOF
tunnel: $tunnel_name
credentials-file: $HOME/.cloudflared/$tunnel_name.json

ingress:
  - hostname: "*.trycloudflare.com"
    service: http://localhost:8000
  - service: http_status:404
EOF
    
    log_success "持久 tunnel 設置完成"
    log_info "使用 '$0 start' 啟動 tunnel"
}

# 啟動 tunnel
start_tunnel() {
    local config_file="$HOME/.cloudflared/config.yml"
    
    if [[ ! -f "$config_file" ]]; then
        log_error "配置文件不存在，請先運行: $0 setup"
        exit 1
    fi
    
    log_info "啟動 tunnel..."
    cloudflared tunnel --config "$config_file" run
}

# 停止 tunnel
stop_tunnel() {
    log_info "停止 tunnel..."
    pkill -f cloudflared || true
    log_success "Tunnel 已停止"
}

# 查看狀態
check_status() {
    log_info "檢查服務狀態..."
    
    # 檢查本地服務
    local port=8000
    if curl -s http://localhost:$port/health > /dev/null; then
        log_success "本地服務運行正常 (端口 $port)"
    else
        log_error "本地服務未運行 (端口 $port)"
    fi
    
    # 檢查 cloudflared 進程
    if pgrep -f cloudflared > /dev/null; then
        log_success "Cloudflared 正在運行"
        log_info "進程 ID: $(pgrep -f cloudflared)"
    else
        log_warning "Cloudflared 未運行"
    fi
    
    # 檢查 tunnel 配置
    local config_file="$HOME/.cloudflared/config.yml"
    if [[ -f "$config_file" ]]; then
        log_success "Tunnel 配置存在"
    else
        log_warning "Tunnel 配置不存在"
    fi
}

# 顯示完整的啟動指南
show_startup_guide() {
    echo ""
    echo "🚀 完整啟動指南："
    echo ""
    echo "1. 安裝 cloudflared："
    echo "   $0 install"
    echo ""
    echo "2. 啟動 Mac Mini 服務："
    echo "   cd mac-processor && ./start.sh"
    echo ""
    echo "3. 啟動 tunnel (二擇一)："
    echo "   a) 快速模式（臨時）: $0 quick"
    echo "   b) 持久模式: $0 setup && $0 start"
    echo ""
    echo "4. 複製 tunnel URL 並在前端配置"
    echo ""
}

# 主邏輯
detect_os

case "${1:-help}" in
    "install")
        install_cloudflared
        ;;
    "quick")
        quick_tunnel ${2:-8000}
        ;;
    "setup")
        setup_tunnel
        ;;
    "start")
        start_tunnel
        ;;
    "stop")
        stop_tunnel
        ;;
    "status")
        check_status
        ;;
    "guide")
        show_startup_guide
        ;;
    "help"|*)
        show_help
        show_startup_guide
        ;;
esac
