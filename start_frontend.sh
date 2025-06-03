#!/bin/bash

echo "🌐 啟動 AI 會議助手前端..."

# 檢查是否在正確目錄
if [ ! -f "package.json" ]; then
    echo "❌ 錯誤：請在專案根目錄執行此腳本"
    echo "   當前目錄：$(pwd)"
    echo "   請執行：cd /path/to/aplay-ai-meeting-tool && ./start_frontend.sh"
    exit 1
fi

# 檢查 Node.js
if ! command -v npm &> /dev/null; then
    echo "❌ 錯誤：未安裝 Node.js"
    echo "   請安裝 Node.js: https://nodejs.org/"
    exit 1
fi

# 檢查並安裝依賴
if [ ! -d "node_modules" ]; then
    echo "📦 安裝前端依賴套件..."
    npm install
fi

# 啟動開發服務器
echo "🎯 啟動前端開發服務器..."
echo "🌐 前端界面: http://localhost:3000"
echo "🔗 確保後端已在 http://localhost:8000 運行"
echo ""
echo "按 Ctrl+C 停止服務"
echo "----------------------------------------"

npm run dev