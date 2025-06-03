# 部署指南

## 🏗️ 系統需求

### Mac Mini 硬體需求
- **CPU**: Apple M1/M2 或 Intel i5 以上
- **記憶體**: 16GB 以上（推薦 32GB）
- **儲存**: 500GB 以上 SSD
- **網路**: 穩定的寬頻連線
- **GPU**: 支援 CUDA 的顯卡（可選，但強烈推薦）

### 軟體需求
- **作業系統**: macOS 11+ 或 Ubuntu 20.04+
- **Python**: 3.8-3.11
- **Node.js**: 16+ (前端開發用)
- **Redis**: 最新穩定版
- **FFmpeg**: 最新版本

## 🚀 快速部署

### 1. 環境準備

```bash
# 更新系統
sudo apt update && sudo apt upgrade -y  # Ubuntu
# 或
brew update && brew upgrade  # macOS

# 安裝基礎依賴
# Ubuntu
sudo apt install -y python3-pip python3-venv redis-server ffmpeg git curl

# macOS
brew install python redis ffmpeg git
```

### 2. 克隆專案

```bash
git clone https://github.com/garyyang1001/aplay-ai-meeting-tool.git
cd aplay-ai-meeting-tool
```

### 3. 後端部署

```bash
# 建立虛擬環境
python3 -m venv whisperx-env
source whisperx-env/bin/activate

# 安裝依賴
cd backend
pip install -r requirements.txt

# 安裝 WhisperX
pip install whisperx
# 或最新版本
pip install git+https://github.com/m-bain/whisperx.git

# 設置環境變數
cp .env.example .env
# 編輯 .env 檔案，填入必要的 API 金鑰
```

### 4. 設置環境變數

```bash
# .env 檔案內容
HF_TOKEN=your_huggingface_token
OPENROUTER_API_KEY=your_openrouter_api_key
REDIS_URL=redis://localhost:6379
UPLOAD_DIR=/tmp/audio_uploads
MAX_FILE_SIZE=100MB
SUPPORTED_LANGUAGES=zh,en,ja,ko
DEFAULT_MODEL_SIZE=large-v2
DEVICE=auto  # auto, cpu, cuda
```

### 5. 測試安裝

```bash
# 測試 WhisperX
python test_whisperx.py

# 測試 API
python -m uvicorn main:app --reload --port 8000
# 瀏覽器開啟 http://localhost:8000/docs
```

### 6. 前端部署

```bash
# 開發模式
npm install
npm run dev

# 生產部署 (Vercel)
npm run build
vercel --prod

# 或部署到 Netlify
netlify deploy --prod --dir dist
```

## 🔧 詳細配置

### Redis 設置

```bash
# Ubuntu 啟動 Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# macOS 啟動 Redis
brew services start redis

# 測試 Redis 連線
redis-cli ping
# 應該回應 PONG
```

### 系統服務設置

```bash
# 建立 systemd 服務檔案
sudo tee /etc/systemd/system/whisperx-api.service > /dev/null <<EOF
[Unit]
Description=WhisperX API Service
After=network.target redis.service
Requires=redis.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$PWD/backend
Environment=PATH=$PWD/whisperx-env/bin
EnvironmentFile=$PWD/backend/.env
ExecStart=$PWD/whisperx-env/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 啟動服務
sudo systemctl daemon-reload
sudo systemctl enable whisperx-api
sudo systemctl start whisperx-api

# 檢查狀態
sudo systemctl status whisperx-api
```

### Nginx 反向代理（可選）

```nginx
# /etc/nginx/sites-available/whisperx-api
server {
    listen 80;
    server_name your-domain.com;
    
    # 重導向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL 證書設置
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    # 安全標頭
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # 檔案上傳大小限制
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支援
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超時設置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;  # 長時間處理
    }
}
```

### 防火牆設置

```bash
# Ubuntu UFW
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8000/tcp  # API (如果直接存取)
sudo ufw enable

# macOS (如果需要)
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on
```

## 📊 監控設置

### 日誌配置

```python
# backend/logging_config.py
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    log_dir = os.getenv('LOG_DIR', '/var/log/whisperx')
    os.makedirs(log_dir, exist_ok=True)
    
    # 設置日誌格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 檔案處理器
    file_handler = RotatingFileHandler(
        f'{log_dir}/whisperx-api.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # 控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    
    # 根日誌器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger
```

### 健康檢查腳本

```bash
#!/bin/bash
# health_check.sh

API_URL="http://localhost:8000/health"
LOG_FILE="/var/log/whisperx/health_check.log"

response=$(curl -s -w "%{http_code}" "$API_URL" -o /dev/null)

if [ "$response" = "200" ]; then
    echo "$(date): API 健康檢查通過" >> "$LOG_FILE"
else
    echo "$(date): API 健康檢查失敗 - HTTP $response" >> "$LOG_FILE"
    # 發送警報（可選）
    # curl -X POST "https://your-webhook-url" -d "API down: $response"
fi
```

```bash
# 加入 crontab
crontab -e
# 每 5 分鐘檢查一次
*/5 * * * * /path/to/health_check.sh
```

### 效能監控

```python
# backend/monitoring.py
import psutil
import GPUtil
from prometheus_client import start_http_server, Gauge

# Prometheus 指標
cpu_usage = Gauge('cpu_usage_percent', 'CPU usage percentage')
memory_usage = Gauge('memory_usage_percent', 'Memory usage percentage')
gpu_usage = Gauge('gpu_usage_percent', 'GPU usage percentage')
active_requests = Gauge('active_requests', 'Number of active requests')

def start_monitoring():
    """啟動 Prometheus 監控"""
    start_http_server(9090)
    
    def update_metrics():
        # CPU 使用率
        cpu_usage.set(psutil.cpu_percent())
        
        # 記憶體使用率
        memory = psutil.virtual_memory()
        memory_usage.set(memory.percent)
        
        # GPU 使用率
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_usage.set(gpus[0].load * 100)
        except:
            pass
    
    # 每 10 秒更新一次
    import threading
    timer = threading.Timer(10.0, update_metrics)
    timer.daemon = True
    timer.start()
```

## 🔧 故障排除

### 常見問題

#### 1. CUDA 相關錯誤
```bash
# 檢查 CUDA 是否可用
python -c "import torch; print(torch.cuda.is_available())"

# 如果 CUDA 不可用，檢查驅動
nvidia-smi

# 重新安裝 PyTorch (CUDA 版本)
pip uninstall torch torchaudio
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

#### 2. 記憶體不足
```python
# 調整批次大小和精度
model = whisperx.load_model(
    "large-v2", 
    device, 
    compute_type="int8",  # 降低精度
    batch_size=8         # 減少批次大小
)
```

#### 3. 音訊格式不支援
```bash
# 安裝額外的音訊編解碼器
sudo apt install ubuntu-restricted-extras  # Ubuntu
brew install ffmpeg --with-libvorbis --with-libvpx  # macOS
```

#### 4. API 回應緩慢
```python
# 啟用非同步處理
from fastapi import BackgroundTasks

@app.post("/process-audio-async")
async def process_audio_async(
    file: UploadFile,
    background_tasks: BackgroundTasks
):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(process_audio_background, file, job_id)
    return {"job_id": job_id, "status": "processing"}
```

### 效能調校

#### 1. 模型快取
```python
# 預載入模型避免冷啟動
class ModelCache:
    def __init__(self):
        self.models = {}
    
    def get_model(self, model_name, device):
        key = f"{model_name}_{device}"
        if key not in self.models:
            self.models[key] = whisperx.load_model(model_name, device)
        return self.models[key]

model_cache = ModelCache()
```

#### 2. 批次處理優化
```python
# 動態調整批次大小
def get_optimal_batch_size(audio_duration, available_memory):
    """根據音訊長度和可用記憶體調整批次大小"""
    if audio_duration < 60:  # 1分鐘以下
        return 16
    elif audio_duration < 300:  # 5分鐘以下
        return 8
    else:
        return 4
```

#### 3. 磁碟空間管理
```bash
# 定期清理暫存檔案
#!/bin/bash
# cleanup.sh
find /tmp/audio_uploads -type f -mtime +1 -delete
find /var/log/whisperx -name "*.log.*" -mtime +7 -delete

# 加入 crontab 每日執行
0 2 * * * /path/to/cleanup.sh
```

## 🚀 生產部署檢核清單

### 部署前檢查
- [ ] 所有環境變數已設置
- [ ] 資料庫/Redis 連線正常
- [ ] SSL 證書已安裝
- [ ] 防火牆規則已配置
- [ ] 日誌目錄權限正確
- [ ] 備份策略已制定

### 部署後驗證
- [ ] API 健康檢查通過
- [ ] 上傳檔案功能正常
- [ ] 轉錄功能準確
- [ ] 說話者辨識有效
- [ ] AI 分析回應正常
- [ ] 效能指標在預期範圍

### 監控告警
- [ ] CPU 使用率 >80% 警報
- [ ] 記憶體使用率 >90% 警報
- [ ] 磁碟空間 <10% 警報
- [ ] API 回應時間 >30秒 警報
- [ ] 錯誤率 >5% 警報

恭喜！🎉 你的 AI 會議助手已經成功部署並運行中。