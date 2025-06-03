#!/bin/bash

# AI Meeting Tool 生產部署腳本
# 自動部署到生產環境

set -e

echo "🚀 AI Meeting Tool 生產部署"
echo "========================"

# 檢查是否為 root 或有 sudo 權限
if [[ $EUID -eq 0 ]]; then
    echo "⚠️  檢測到 root 權限"
elif sudo -n true 2>/dev/null; then
    echo "✅ 檢測到 sudo 權限"
else
    echo "❌ 需要 sudo 權限進行系統配置"
    exit 1
fi

# 檢查環境
ENV=${1:-production}
echo "📍 部署環境: $ENV"

# 設定變數
APP_USER="whisperx"
APP_DIR="/opt/ai-meeting-tool"
SERVICE_NAME="whisperx-api"
NGINX_CONF="/etc/nginx/sites-available/ai-meeting-tool"

# 建立應用使用者
echo "\n👤 建立應用使用者..."
if ! id "$APP_USER" &>/dev/null; then
    sudo useradd -r -s /bin/bash -d $APP_DIR $APP_USER
    echo "✅ 使用者 $APP_USER 建立完成"
else
    echo "✅ 使用者 $APP_USER 已存在"
fi

# 建立應用目錄
echo "\n📁 建立應用目錄..."
sudo mkdir -p $APP_DIR
sudo mkdir -p /var/log/whisperx
sudo mkdir -p /var/lib/whisperx

# 複製應用檔案
echo "\n📦 複製應用檔案..."
sudo cp -r backend $APP_DIR/
sudo cp -r docs $APP_DIR/
sudo cp -r scripts $APP_DIR/
sudo cp README.md $APP_DIR/

# 設定檔案權限
echo "\n🔐 設定檔案權限..."
sudo chown -R $APP_USER:$APP_USER $APP_DIR
sudo chown -R $APP_USER:$APP_USER /var/log/whisperx
sudo chown -R $APP_USER:$APP_USER /var/lib/whisperx

# 設定 Python 環境
echo "\n🐍 設定 Python 環境..."
sudo -u $APP_USER bash << 'EOF'
cd /opt/ai-meeting-tool/backend
python3 -m venv whisperx-env
source whisperx-env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install git+https://github.com/m-bain/whisperx.git
EOF

echo "✅ Python 環境設定完成"

# 設定環境變數檔案
echo "\n⚙️  設定環境變數..."
if [[ ! -f "$APP_DIR/backend/.env" ]]; then
    sudo -u $APP_USER cp $APP_DIR/backend/.env.example $APP_DIR/backend/.env
    echo "⚠️  請編輯 $APP_DIR/backend/.env 設定 API 金鑰"
fi

# 安裝系統服務
echo "\n🔧 建立 systemd 服務..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << EOF
[Unit]
Description=WhisperX API Service
After=network.target redis.service
Requires=redis.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/backend
Environment=PATH=$APP_DIR/backend/whisperx-env/bin
EnvironmentFile=$APP_DIR/backend/.env
ExecStart=$APP_DIR/backend/whisperx-env/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

# 資源限制
LimitNOFILE=65536
LimitNPROC=4096

# 安全設定
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR /var/log/whisperx /var/lib/whisperx /tmp

[Install]
WantedBy=multi-user.target
EOF

# 設定 Redis
echo "\n🗄️  設定 Redis..."
sudo systemctl enable redis-server
sudo systemctl start redis-server

# 設定 Nginx (如果安裝了)
echo "\n🌐 設定 Nginx..."
if command -v nginx &> /dev/null; then
    sudo tee $NGINX_CONF > /dev/null << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # 請修改為實際域名
    
    # 重導向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;  # 請修改為實際域名
    
    # SSL 憑證 (請修改路徑)
    # ssl_certificate /path/to/certificate.crt;
    # ssl_certificate_key /path/to/private.key;
    
    # 安全標頭
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # 檔案上傳大小限制
    client_max_body_size 100M;
    
    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支援
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超時設定
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;
    }
    
    # 健康檢查
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
    
    # 靜態檔案 (如果有前端)
    location / {
        root /var/www/ai-meeting-tool;
        try_files $uri $uri/ /index.html;
    }
}
EOF
    
    echo "✅ Nginx 配置檔案已建立"
    echo "⚠️  請修改域名和 SSL 憑證路徑"
    
    # 不自動啟用，讓使用者手動處理
    echo "💡 啟用 Nginx 配置: sudo ln -s $NGINX_CONF /etc/nginx/sites-enabled/"
else
    echo "⚠️  Nginx 未安裝，跳過 web 伺服器配置"
fi

# 設定防火牆 (Ubuntu UFW)
echo "\n🔥 設定防火牆..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 22/tcp    # SSH
    sudo ufw allow 80/tcp    # HTTP
    sudo ufw allow 443/tcp   # HTTPS
    # sudo ufw allow 8000/tcp  # API (如果直接存取)
    
    if ! sudo ufw status | grep -q "Status: active"; then
        echo "💡 啟用防火牆: sudo ufw enable"
    fi
fi

# 設定日誌輪換
echo "\n📋 設定日誌輪換..."
sudo tee /etc/logrotate.d/whisperx > /dev/null << 'EOF'
/var/log/whisperx/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 whisperx whisperx
    postrotate
        systemctl reload whisperx-api || true
    endscript
}
EOF

# 設定清理腳本
echo "\n🧹 設定清理腳本..."
sudo tee /etc/cron.daily/whisperx-cleanup > /dev/null << 'EOF'
#!/bin/bash
# 清理過期的暫存檔案
find /tmp/audio_uploads -type f -mtime +1 -delete 2>/dev/null || true
find /var/log/whisperx -name "*.log.*" -mtime +7 -delete 2>/dev/null || true
EOF

sudo chmod +x /etc/cron.daily/whisperx-cleanup

# 建立監控腳本
echo "\n📊 建立監控腳本..."
sudo tee /usr/local/bin/whisperx-monitor > /dev/null << 'EOF'
#!/bin/bash

# WhisperX 服務監控腳本
SERVICE="whisperx-api"
API_URL="http://localhost:8000/health"
LOG_FILE="/var/log/whisperx/monitor.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# 檢查服務狀態
if ! systemctl is-active --quiet $SERVICE; then
    log_message "ERROR: $SERVICE 服務未運行，嘗試重啟"
    systemctl start $SERVICE
    sleep 10
fi

# 檢查 API 健康狀態
response=$(curl -s -w "%{http_code}" "$API_URL" -o /dev/null --max-time 10)

if [ "$response" = "200" ]; then
    log_message "INFO: API 健康檢查正常"
else
    log_message "ERROR: API 健康檢查失敗 - HTTP $response"
    # 可以在這裡加入通知邏輯
fi

# 檢查磁碟空間
disk_usage=$(df /tmp | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$disk_usage" -gt 90 ]; then
    log_message "WARNING: 磁碟使用量過高: ${disk_usage}%"
fi

# 檢查記憶體使用
mem_usage=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')
if [ "$mem_usage" -gt 90 ]; then
    log_message "WARNING: 記憶體使用量過高: ${mem_usage}%"
fi
EOF

sudo chmod +x /usr/local/bin/whisperx-monitor

# 設定監控 cron
echo "*/5 * * * * root /usr/local/bin/whisperx-monitor" | sudo tee -a /etc/crontab

# 啟動服務
echo "\n🚀 啟動服務..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

# 等待服務啟動
echo "⏳ 等待服務啟動..."
sleep 5

# 檢查服務狀態
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ $SERVICE_NAME 服務啟動成功"
else
    echo "❌ $SERVICE_NAME 服務啟動失敗"
    echo "檢查日誌: sudo journalctl -u $SERVICE_NAME -f"
    exit 1
fi

# 測試 API
echo "\n🧪 測試 API..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API 健康檢查通過"
else
    echo "❌ API 健康檢查失敗"
fi

echo "\n🎉 部署完成！"
echo "================="
echo
echo "✅ 已完成的設定:"
echo "  - 建立使用者: $APP_USER"
echo "  - 安裝應用到: $APP_DIR"
echo "  - 建立 systemd 服務: $SERVICE_NAME"
echo "  - 設定日誌輪換和清理"
echo "  - 建立監控腳本"
echo
echo "⚠️  下一步:"
echo "1. 編輯 $APP_DIR/backend/.env 設定 API 金鑰"
echo "2. 重啟服務: sudo systemctl restart $SERVICE_NAME"
echo "3. 如果使用 Nginx，設定 SSL 憑證和域名"
echo "4. 設定備份策略"
echo
echo "🔧 管理指令:"
echo "  - 查看狀態: sudo systemctl status $SERVICE_NAME"
echo "  - 查看日誌: sudo journalctl -u $SERVICE_NAME -f"
echo "  - 重啟服務: sudo systemctl restart $SERVICE_NAME"
echo "  - 監控日誌: tail -f /var/log/whisperx/monitor.log"
echo
echo "📊 API 端點:"
echo "  - 健康檢查: http://localhost:8000/health"
echo "  - API 文檔: http://localhost:8000/docs"
echo "  - 系統統計: http://localhost:8000/stats"
echo
echo "🎊 享受你的 AI 會議助手！"