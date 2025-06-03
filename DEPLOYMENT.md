# 🚀 AI 會議工具完整部署指南

> 從零開始部署 AI 會議工具的詳細步驟指南

## 🎯 部署概覽

本指南將協助您在任何環境中成功部署 AI 會議工具，支援以下部署模式：

- 🖥️ **本地開發環境** - 適合開發和測試
- 🏠 **家用/辦公室部署** - Mac Mini + 個人使用
- ☁️ **雲端部署** - 可擴展的生產環境
- 🔧 **混合部署** - 前端雲端 + 後端本地

---

## 📋 部署前檢查清單

### ✅ **硬體需求**

| 組件 | 最低配置 | 建議配置 | 企業配置 |
|------|----------|----------|----------|
| **處理器** | 4核心 2.5GHz | 8核心 3.0GHz | 16核心 + GPU |
| **記憶體** | 8GB RAM | 16GB RAM | 32GB RAM |
| **存儲** | 50GB SSD | 100GB SSD | 500GB NVMe |
| **網路** | 10Mbps | 50Mbps | 100Mbps+ |

### ✅ **軟體需求**

- **作業系統**: macOS 10.15+ / Ubuntu 18.04+ / Windows 10+ (WSL2)
- **Node.js**: v18.0.0 或更高版本
- **Python**: 3.8-3.11 (推薦 3.10)
- **Git**: 最新版本

### ✅ **服務帳號**

- **OpenRouter**: [註冊](https://openrouter.ai/) 並獲取 API Key
- **Hugging Face**: [註冊](https://huggingface.co/) 並創建 Access Token
- **Firebase**: [創建專案](https://console.firebase.google.com/) 並啟用相關服務

---

## 🚀 方案一：一鍵部署（推薦）

### 步驟 1: 下載專案

```bash
# 克隆專案
git clone https://github.com/garyyang1001/aplay-ai-meeting-tool.git
cd aplay-ai-meeting-tool

# 切換到最新分支
git checkout refactor/align-architecture-config
```

### 步驟 2: 執行一鍵設置

```bash
# 賦予執行權限
chmod +x setup.sh

# 執行自動設置
./setup.sh
```

設置腳本將：
- ✅ 檢查系統需求
- ✅ 安裝前端依賴
- ✅ 設置 Mac Mini 處理服務
- ✅ 配置 Cloudflare Tunnel
- ✅ 創建啟動腳本

### 步驟 3: 配置服務

1. **設置 OpenRouter API Key**
   ```bash
   # 編輯前端環境配置
   nano .env
   
   # 設置 API Key
   VITE_OPENROUTER_API_KEY=your_actual_api_key
   ```

2. **設置 Hugging Face Token**
   ```bash
   # 編輯 Mac Mini 環境配置
   nano mac-processor/.env
   
   # 設置 Token
   HF_TOKEN=your_actual_token
   ```

3. **設置 Firebase（可選）**
   ```bash
   # 下載 Firebase 服務帳戶金鑰
   # 放置在 mac-processor/firebase-credentials.json
   
   # 或在 .env 中設置各項 Firebase 配置
   ```

### 步驟 4: 啟動服務

```bash
# 一鍵啟動所有服務
./start_all.sh

# 或分別啟動
./start_frontend.sh                    # 前端服務
cd mac-processor && ./start.sh        # Mac Mini 服務
cd mac-processor && ./tunnel.sh quick # Cloudflare Tunnel
```

### 步驟 5: 驗證部署

```bash
# 執行系統測試
chmod +x test.sh
./test.sh
```

---

## 🔧 方案二：手動部署

### 1. 前端部署

```bash
# 安裝依賴
npm install

# 配置環境
cp .env.example .env
nano .env  # 編輯配置

# 開發模式
npm run dev

# 生產構建
npm run build
npm run preview
```

### 2. Mac Mini 服務部署

```bash
cd mac-processor

# 創建 Python 環境
python3 -m venv venv
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 配置環境
cp .env.example .env
nano .env  # 設置 HF_TOKEN 等

# 啟動服務
python3 main.py
```

### 3. Cloudflare Tunnel 設置

```bash
cd mac-processor

# 安裝 cloudflared
# macOS
brew install cloudflared

# Ubuntu/Debian
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb

# 啟動 tunnel
cloudflared tunnel --url http://localhost:8000
```

---

## ☁️ 方案三：雲端部署

### 3.1 前端部署到 Vercel

```bash
# 安裝 Vercel CLI
npm i -g vercel

# 部署
vercel

# 設置環境變數
vercel env add VITE_OPENROUTER_API_KEY
vercel env add VITE_FIREBASE_API_KEY
# ... 其他環境變數
```

### 3.2 後端部署到 Railway/Render

**Dockerfile 範例：**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製代碼
COPY . .

# 暴露端口
EXPOSE 8000

# 啟動命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.3 部署到 AWS EC2

```bash
# 1. 創建 EC2 實例 (t3.large 或更高)
# 2. 安裝依賴
sudo apt update
sudo apt install -y python3 python3-pip nodejs npm git

# 3. 克隆專案
git clone https://github.com/garyyang1001/aplay-ai-meeting-tool.git
cd aplay-ai-meeting-tool

# 4. 執行設置
./setup.sh

# 5. 配置反向代理 (Nginx)
sudo apt install nginx
sudo cp configs/nginx.conf /etc/nginx/sites-available/ai-meeting-tool
sudo ln -s /etc/nginx/sites-available/ai-meeting-tool /etc/nginx/sites-enabled/
sudo systemctl reload nginx

# 6. 設置 SSL 證書 (Let's Encrypt)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 🏢 方案四：企業部署

### 4.1 Kubernetes 部署

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-meeting-processor
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-meeting-processor
  template:
    metadata:
      labels:
        app: ai-meeting-processor
    spec:
      containers:
      - name: processor
        image: ai-meeting-tool:latest
        ports:
        - containerPort: 8000
        env:
        - name: HF_TOKEN
          valueFrom:
            secretKeyRef:
              name: ai-meeting-secrets
              key: hf-token
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "8Gi"
            cpu: "4000m"
---
apiVersion: v1
kind: Service
metadata:
  name: ai-meeting-service
spec:
  selector:
    app: ai-meeting-processor
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 4.2 Docker Compose 部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - VITE_MAC_MINI_URL=http://processor:8000
    depends_on:
      - processor

  processor:
    build:
      context: ./mac-processor
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - HF_TOKEN=${HF_TOKEN}
      - FIREBASE_SERVICE_ACCOUNT_KEY=${FIREBASE_KEY}
    volumes:
      - ./logs:/app/logs
      - ./temp:/app/temp
    restart: unless-stopped

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

volumes:
  logs:
  temp:
```

---

## 🔒 安全配置

### 防火牆設置

```bash
# Ubuntu UFW
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8000/tcp  # API (僅限內部)
sudo ufw enable

# CentOS/RHEL Firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

### SSL/TLS 配置

```nginx
# /etc/nginx/sites-available/ai-meeting-tool
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 環境變數管理

```bash
# 生產環境使用 systemd 環境檔案
sudo mkdir -p /etc/systemd/system/ai-meeting.service.d/
cat > /etc/systemd/system/ai-meeting.service.d/environment.conf << EOF
[Service]
Environment="HF_TOKEN=your_token"
Environment="OPENROUTER_API_KEY=your_key"
Environment="NODE_ENV=production"
EOF
```

---

## 📊 監控和維護

### 日誌管理

```bash
# 設置 logrotate
cat > /etc/logrotate.d/ai-meeting-tool << EOF
/var/log/ai-meeting-tool/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    postrotate
        systemctl reload ai-meeting-processor
    endscript
}
EOF
```

### 效能監控

```bash
# 安裝監控工具
# Prometheus + Grafana
docker run -d -p 9090:9090 prom/prometheus
docker run -d -p 3001:3000 grafana/grafana

# 系統監控
sudo apt install htop iotop nethogs
```

### 自動備份

```bash
# 創建備份腳本
cat > /usr/local/bin/ai-meeting-backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/ai-meeting-tool"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 備份配置
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
    /opt/ai-meeting-tool/.env \
    /opt/ai-meeting-tool/mac-processor/.env \
    /opt/ai-meeting-tool/mac-processor/firebase-credentials.json

# 備份日誌
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz \
    /var/log/ai-meeting-tool/

# 清理舊備份 (保留 7 天)
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x /usr/local/bin/ai-meeting-backup.sh

# 設置定時任務
echo "0 2 * * * /usr/local/bin/ai-meeting-backup.sh" | crontab -
```

---

## 🐛 故障排除

### 常見部署問題

#### 1. 端口衝突
```bash
# 查找佔用端口的進程
sudo lsof -i :8000
sudo lsof -i :5173

# 終止進程
sudo kill -9 <PID>
```

#### 2. 權限問題
```bash
# 設置正確的檔案權限
chmod +x setup.sh start_frontend.sh test.sh
chmod +x mac-processor/start.sh mac-processor/tunnel.sh

# 設置目錄權限
chmod 755 mac-processor/logs mac-processor/temp
```

#### 3. Python 模組問題
```bash
# 重新建立虛擬環境
cd mac-processor
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Firebase 連接問題
```bash
# 驗證 Firebase 金鑰
cd mac-processor
python3 -c "
import firebase_admin
from firebase_admin import credentials
cred = credentials.Certificate('firebase-credentials.json')
app = firebase_admin.initialize_app(cred)
print('Firebase 連接成功')
"
```

### 效能調優

#### CPU 優化
```bash
# 設置 CPU affinity
taskset -c 0-3 python3 main.py

# 設置程序優先級
nice -n -5 python3 main.py
```

#### 記憶體優化
```bash
# 限制記憶體使用
ulimit -v 8388608  # 8GB

# 設置 swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📈 擴展和升級

### 水平擴展

```bash
# 使用 HAProxy 負載均衡
# /etc/haproxy/haproxy.cfg
backend ai_processors
    balance roundrobin
    server proc1 10.0.1.10:8000 check
    server proc2 10.0.1.11:8000 check
    server proc3 10.0.1.12:8000 check
```

### 垂直擴展

```bash
# 增加處理器數量
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8

# 使用 GPU 加速
export CUDA_VISIBLE_DEVICES=0,1
```

### 升級流程

```bash
# 1. 備份當前版本
./backup.sh

# 2. 拉取最新代碼
git pull origin main

# 3. 更新依賴
npm install
cd mac-processor && pip install -r requirements.txt

# 4. 執行測試
./test.sh

# 5. 重啟服務
./restart.sh
```

---

## 📞 支援和維護

### 獲取幫助

- **文檔**: [README.md](../README.md)
- **問題回報**: [GitHub Issues](https://github.com/garyyang1001/aplay-ai-meeting-tool/issues)
- **討論**: [GitHub Discussions](https://github.com/garyyang1001/aplay-ai-meeting-tool/discussions)

### 社群支援

- **更新通知**: 訂閱 GitHub releases
- **安全更新**: 定期檢查依賴更新
- **功能請求**: 提交 feature request

---

**🎉 部署完成！享受您的 AI 會議助手！**

需要更多協助？請查看 [故障排除指南](mac-processor/README.md#故障排除) 或聯繫我們的社群。
