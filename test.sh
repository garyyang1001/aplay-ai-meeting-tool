#!/bin/bash

# AI 會議工具測試驗證腳本
# 自動測試系統各個組件的功能

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

# 測試結果統計
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

# 測試函數
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    echo -n "測試 ${test_name}... "
    
    if eval "$test_command" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ 通過${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}❌ 失敗${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# HTTP 測試函數
test_http_endpoint() {
    local url="$1"
    local expected_code="${2:-200}"
    
    local response_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    
    if [ "$response_code" = "$expected_code" ]; then
        return 0
    else
        return 1
    fi
}

# JSON 響應測試
test_json_response() {
    local url="$1"
    local key="$2"
    
    local response=$(curl -s "$url" 2>/dev/null || echo "{}")
    
    if echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('$key', ''))
    sys.exit(0)
except:
    sys.exit(1)
" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 主測試函數
main() {
    log_header "AI 會議工具系統測試"
    
    echo "🧪 開始執行自動化測試..."
    echo ""
    
    # 1. 環境檢查
    log_header "1. 環境檢查"
    
    run_test "Node.js 可用性" "command -v node"
    run_test "Python3 可用性" "command -v python3"
    run_test "npm 可用性" "command -v npm"
    run_test "curl 可用性" "command -v curl"
    
    # Node.js 版本檢查
    if command -v node >/dev/null 2>&1; then
        local node_version=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
        run_test "Node.js 版本 >= 18" "[ $node_version -ge 18 ]"
    fi
    
    # Python 版本檢查
    if command -v python3 >/dev/null 2>&1; then
        run_test "Python3 版本檢查" "python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'"
    fi
    
    echo ""
    
    # 2. 前端測試
    log_header "2. 前端環境測試"
    
    run_test "package.json 存在" "[ -f package.json ]"
    run_test ".env 檔案存在" "[ -f .env ]"
    run_test "index.html 存在" "[ -f index.html ]"
    run_test "manifest.json 存在" "[ -f manifest.json ]"
    
    # 檢查前端依賴
    if [ -f "package.json" ]; then
        run_test "前端依賴安裝" "[ -d node_modules ]"
        run_test "TypeScript 文件存在" "[ -f src/main.ts ]"
        run_test "Firebase 服務存在" "[ -f src/firebase-service.ts ]"
        run_test "增強錄音器存在" "[ -f src/enhanced-recorder.ts ]"
    fi
    
    echo ""
    
    # 3. Mac Mini 服務測試
    log_header "3. Mac Mini 服務測試"
    
    if [ -d "mac-processor" ]; then
        cd mac-processor
        
        run_test "Mac Mini 主程式存在" "[ -f main.py ]"
        run_test "Python 依賴文件存在" "[ -f requirements.txt ]"
        run_test "環境配置存在" "[ -f .env.example ]"
        run_test "啟動腳本存在" "[ -f start.sh ] && [ -x start.sh ]"
        run_test "Tunnel 腳本存在" "[ -f tunnel.sh ] && [ -x tunnel.sh ]"
        
        # 檢查 Python 虛擬環境
        if [ -d "venv" ]; then
            run_test "Python 虛擬環境可用" "[ -f venv/bin/activate ] || [ -f venv/Scripts/activate.bat ]"
            
            # 激活虛擬環境並測試
            if [ -f "venv/bin/activate" ]; then
                source venv/bin/activate
                run_test "FastAPI 已安裝" "python3 -c 'import fastapi'"
                run_test "PyTorch 已安裝" "python3 -c 'import torch'"
                
                # 嘗試導入 pyannote（可能需要 HF Token）
                if [ -f ".env" ] && grep -q "HF_TOKEN=" .env && ! grep -q "your_huggingface_token_here" .env; then
                    run_test "pyannote.audio 可用" "python3 -c 'from pyannote.audio import Pipeline; print(\"OK\")'"
                else
                    log_warning "跳過 pyannote 測試 - HF_TOKEN 未設置"
                fi
                
                deactivate 2>/dev/null || true
            fi
        else
            log_warning "Python 虛擬環境未建立"
        fi
        
        cd ..
    else
        log_error "mac-processor 目錄不存在"
    fi
    
    echo ""
    
    # 4. 服務可用性測試
    log_header "4. 服務可用性測試"
    
    # 檢查前端服務
    if test_http_endpoint "http://localhost:5173" "200"; then
        log_success "前端服務正在運行 (localhost:5173)"
        
        run_test "前端首頁載入" "test_http_endpoint 'http://localhost:5173' '200'"
        run_test "manifest.json 可存取" "test_http_endpoint 'http://localhost:5173/manifest.json' '200'"
        
    elif test_http_endpoint "http://localhost:3000" "200"; then
        log_success "前端服務正在運行 (localhost:3000)"
        
    else
        log_warning "前端服務未運行 - 請執行 'npm run dev' 或 './start_frontend.sh'"
    fi
    
    # 檢查 Mac Mini 服務
    if test_http_endpoint "http://localhost:8000" "200"; then
        log_success "Mac Mini 服務正在運行"
        
        run_test "Mac Mini 健康檢查" "test_http_endpoint 'http://localhost:8000/health' '200'"
        run_test "Mac Mini API 響應" "test_json_response 'http://localhost:8000/health' 'status'"
        
        # 測試 API 端點
        run_test "處理端點可用" "test_http_endpoint 'http://localhost:8000/process' '422'"  # 422 表示需要參數
        
    else
        log_warning "Mac Mini 服務未運行 - 請執行 'cd mac-processor && ./start.sh'"
    fi
    
    echo ""
    
    # 5. 配置檢查
    log_header "5. 配置檢查"
    
    # 檢查前端環境變數
    if [ -f ".env" ]; then
        run_test "OpenRouter API Key 已設置" "grep -q 'VITE_OPENROUTER_API_KEY=' .env && ! grep -q 'your_api_key_here' .env"
        run_test "Firebase 配置已設置" "grep -q 'VITE_FIREBASE_API_KEY=' .env"
        
        if grep -q "VITE_MAC_MINI_URL=" .env && ! grep -q "your_tunnel_url_here" .env; then
            log_success "Mac Mini URL 已配置"
        else
            log_warning "Mac Mini URL 未配置 - 請設置 VITE_MAC_MINI_URL"
        fi
    else
        log_error "前端 .env 文件不存在"
    fi
    
    # 檢查 Mac Mini 環境變數
    if [ -f "mac-processor/.env" ]; then
        cd mac-processor
        run_test "HF Token 已設置" "grep -q 'HF_TOKEN=' .env && ! grep -q 'your_huggingface_token_here' .env"
        run_test "服務端口配置" "grep -q 'PORT=' .env"
        cd ..
    else
        log_warning "Mac Mini .env 文件不存在"
    fi
    
    echo ""
    
    # 6. Cloudflare Tunnel 測試
    log_header "6. Cloudflare Tunnel 測試"
    
    run_test "cloudflared 可用性" "command -v cloudflared"
    
    if command -v cloudflared >/dev/null 2>&1; then
        local version=$(cloudflared version 2>/dev/null | head -1 || echo "unknown")
        log_success "cloudflared 版本: $version"
    else
        log_warning "cloudflared 未安裝 - 請執行 'cd mac-processor && ./tunnel.sh install'"
    fi
    
    echo ""
    
    # 7. 整合測試
    log_header "7. 整合測試"
    
    # 檢查完整的處理鏈
    if test_http_endpoint "http://localhost:5173" "200" && test_http_endpoint "http://localhost:8000/health" "200"; then
        log_success "前端和後端服務都在運行"
        run_test "完整系統可用" "true"
        
        # 簡單的 API 測試
        if curl -s "http://localhost:8000/health" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('status') == 'healthy':
        sys.exit(0)
    else:
        sys.exit(1)
except:
    sys.exit(1)
" >/dev/null 2>&1; then
            log_success "Mac Mini 服務健康檢查通過"
        else
            log_warning "Mac Mini 服務健康檢查異常"
        fi
    else
        log_warning "系統未完全啟動 - 請確保前後端服務都在運行"
    fi
    
    echo ""
    
    # 測試結果統計
    log_header "測試結果統計"
    
    echo "📊 測試摘要:"
    echo "  總計: $TESTS_TOTAL"
    echo -e "  通過: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "  失敗: ${RED}$TESTS_FAILED${NC}"
    
    local success_rate=0
    if [ $TESTS_TOTAL -gt 0 ]; then
        success_rate=$((TESTS_PASSED * 100 / TESTS_TOTAL))
    fi
    
    echo "  成功率: $success_rate%"
    echo ""
    
    # 建議
    if [ $TESTS_FAILED -eq 0 ]; then
        log_success "🎉 所有測試通過！系統已準備就緒"
        echo ""
        echo "🚀 下一步操作："
        echo "  1. 訪問 http://localhost:5173 開始使用"
        echo "  2. 點擊麥克風開始錄音"
        echo "  3. 享受 AI 會議分析功能！"
        
    elif [ $success_rate -ge 80 ]; then
        log_warning "⚠️  大部分測試通過，但有一些問題需要注意"
        echo ""
        echo "🔧 建議檢查："
        echo "  1. 確保所有環境變數已正確設置"
        echo "  2. 檢查服務是否完全啟動"
        echo "  3. 查看上方失敗的測試項目"
        
    else
        log_error "❌ 多個測試失敗，請檢查系統配置"
        echo ""
        echo "🛠️  請執行以下操作："
        echo "  1. 重新運行 ./setup.sh 進行設置"
        echo "  2. 檢查依賴是否正確安裝"
        echo "  3. 確認環境變數配置"
        echo "  4. 查看服務日誌了解詳細錯誤"
    fi
    
    echo ""
    echo "📚 更多幫助："
    echo "  - 查看 README.md 獲取詳細說明"
    echo "  - 查看 mac-processor/README.md 了解後端配置"
    echo "  - 提交 Issue: https://github.com/garyyang1001/aplay-ai-meeting-tool/issues"
    
    # 返回碼
    if [ $TESTS_FAILED -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# 顯示使用說明
show_help() {
    echo "AI 會議工具測試腳本"
    echo ""
    echo "使用方法:"
    echo "  $0          - 執行完整測試"
    echo "  $0 --help  - 顯示此說明"
    echo "  $0 --quick - 快速測試（跳過耗時檢查）"
    echo ""
}

# 快速測試模式
quick_test() {
    log_header "快速測試模式"
    
    # 只測試基本功能
    run_test "Node.js 可用" "command -v node"
    run_test "Python3 可用" "command -v python3"
    run_test "前端文件存在" "[ -f index.html ]"
    run_test "Mac Mini 服務存在" "[ -f mac-processor/main.py ]"
    
    if test_http_endpoint "http://localhost:5173" "200"; then
        log_success "前端服務運行中"
    else
        log_warning "前端服務未運行"
    fi
    
    if test_http_endpoint "http://localhost:8000/health" "200"; then
        log_success "Mac Mini 服務運行中"
    else
        log_warning "Mac Mini 服務未運行"
    fi
    
    echo ""
    echo "✅ 快速測試完成"
}

# 主邏輯
case "${1:-}" in
    "--help"|"-h")
        show_help
        ;;
    "--quick"|"-q")
        quick_test
        ;;
    "")
        main
        ;;
    *)
        echo "未知參數: $1"
        show_help
        exit 1
        ;;
esac
