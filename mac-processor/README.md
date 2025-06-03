# 🖥️ Mac Mini 音頻處理服務

> 專為 AI 會議工具設計的高效能音頻處理和說話者識別服務
> 
> 使用 pyannote.audio 3.1 提供專業級說話者識別功能

## 📋 概述

Mac Mini 處理服務是 AI 會議工具的核心組件，負責：

- 🎯 **專業說話者識別** - 使用 pyannote.audio 3.1 模型
- 🔄 **音頻檔案處理** - 支援多種音頻格式
- 🤝 **前端 API 整合** - 提供 RESTful API 接口
- ☁️ **Firebase 同步** - 自動同步處理結果
- 🔒 **安全隧道存取** - 透過 Cloudflare Tunnel 安全連接

## 🏗️ 架構設計

```
前端錄音 → Firebase Storage → Cloudflare Tunnel → Mac Mini 處理服務
                                                        ↓
                                                   pyannote.audio
                                                        ↓
                                              Firebase 結果同步 → 前端顯示
```

### 核心組件

- **FastAPI 應用** - 高效能 Python Web 框架
- **pyannote.audio Pipeline** - 最先進的說話者識別模型
- **Firebase Admin SDK** - 雲端存儲和資料庫操作
- **背景任務處理** - 非同步音頻處理
- **健康檢查系統** - 服務狀態監控

## 🚀 快速開始

### 📋 系統需求

- **作業系統**: macOS 10.15+ / Ubuntu 18.04+
- **Python**: 3.8 - 3.11 (推薦 3.10)
- **記憶體**: 至少 8GB (推薦 16GB)
- **存儲**: 5GB 可用空間
- **網路**: 穩定的網際網路連接

### ⚡ 自動安裝

```bash
# 在專案根目錄執行
./setup.sh

# 或者進入 mac-processor 目錄
cd mac-processor
./start.sh
```

### 🔧 手動安裝

#### 1. 環境準備

```bash
# 進入 Mac Mini 服務目錄
cd mac-processor

# 創建 Python 虛擬環境
python3 -m venv venv

# 啟動虛擬環境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

# 升級 pip
pip install --upgrade pip

# 安裝依賴
pip install -r requirements.txt
```

#### 2. 環境配置

```bash
# 複製環境變數範本
cp .env.example .env

# 編輯配置文件
nano .env  # 或使用您喜歡的編輯器
```

**必要配置項目：**

```bash
# Hugging Face Token (必須)
HF_TOKEN=your_huggingface_token_here

# 服務端口 (可選)
PORT=8000
HOST=0.0.0.0

# Firebase 配置 (可選，但建議設置)
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json

# GPU 記憶體管理 (可選)
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

#### 3. Hugging Face 設置

1. **獲取 Token**
   - 訪問 [Hugging Face Tokens](https://huggingface.co/settings/tokens)
   - 創建新的 Access Token (Read 權限即可)

2. **接受模型條款**
   - [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
   - [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)

3. **驗證設置**
   ```bash
   python3 -c "
   from pyannote.audio import Pipeline
   import os
   pipeline = Pipeline.from_pretrained(
       'pyannote/speaker-diarization-3.1',
       use_auth_token=os.getenv('HF_TOKEN')
   )
   print('✅ 模型載入成功')
   "
   ```

#### 4. Firebase 設置 (可選)

```bash
# 1. 從 Firebase Console 下載服務帳戶金鑰
# 2. 將檔案命名為 firebase-credentials.json
# 3. 放置在 mac-processor 目錄中

# 或者使用環境變數
export FIREBASE_SERVICE_ACCOUNT_KEY='{"type":"service_account",...}'
```

#### 5. 啟動服務

```bash
# 開發模式
./start.sh dev

# 生產模式
./start.sh prod

# 或直接執行
python3 main.py
```

## 🔗 Cloudflare Tunnel 設置

### 快速開始

```bash
# 安裝 cloudflared
./tunnel.sh install

# 啟動快速 tunnel (測試用)
./tunnel.sh quick

# 設置持久 tunnel (生產用)
./tunnel.sh setup
./tunnel.sh start
```

### 手動設置

```bash
# 1. 安裝 cloudflared
brew install cloudflared  # macOS
# 或下載二進制檔案

# 2. 啟動 tunnel
cloudflared tunnel --url http://localhost:8000

# 3. 複製產生的 URL
# 例如: https://abc-def-ghi.trycloudflare.com

# 4. 更新前端配置
# 在專案根目錄的 .env 文件中設置：
# VITE_MAC_MINI_URL=https://abc-def-ghi.trycloudflare.com
```

## 📡 API 文檔

### 端點概覽

| 端點 | 方法 | 說明 |
|------|------|------|
| `/` | GET | 服務基本信息 |
| `/health` | GET | 詳細健康檢查 |
| `/process` | POST | 處理音頻請求 |
| `/status/{job_id}` | GET | 查詢任務狀態 |
| `/upload` | POST | 直接上傳處理 |

### 主要 API

#### 1. 健康檢查

```bash
curl http://localhost:8000/health
```

**回應範例：**
```json
{
  "status": "healthy",
  "services": {
    "pyannote": true,
    "firebase": true,
    "processing_jobs": 0
  },
  "system": {
    "timestamp": "2024-01-01T12:00:00",
    "temp_dir": "/tmp"
  }
}
```

#### 2. 處理音頻

```bash
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test_job_123",
    "audio_url": "https://example.com/audio.wav",
    "transcript": [
      {"text": "Hello world", "timestamp": 1000}
    ],
    "num_speakers": 2
  }'
```

**回應範例：**
```json
{
  "status": "processing",
  "job_id": "test_job_123",
  "message": "音頻處理已開始"
}
```

#### 3. 查詢狀態

```bash
curl http://localhost:8000/status/test_job_123
```

**回應範例：**
```json
{
  "job_id": "test_job_123",
  "status": "completed",
  "speakers": [
    {
      "speaker": "SPEAKER_00",
      "start": 0.0,
      "end": 5.2,
      "duration": 5.2
    }
  ],
  "enhanced_transcript": [
    {
      "text": "Hello world",
      "speaker": "SPEAKER_00",
      "timestamp": 1.0,
      "enhanced": true
    }
  ],
  "speaker_count": 2,
  "total_duration": 60.5
}
```

#### 4. 直接上傳

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@meeting.wav" \
  -F "num_speakers=3"
```

## 🔧 配置說明

### 環境變數

| 變數名 | 必需 | 預設值 | 說明 |
|--------|------|--------|------|
| `HF_TOKEN` | ✅ | - | Hugging Face API Token |
| `PORT` | ❌ | 8000 | 服務端口 |
| `HOST` | ❌ | 0.0.0.0 | 綁定地址 |
| `FIREBASE_CREDENTIALS_PATH` | ❌ | - | Firebase 金鑰檔案路徑 |
| `FIREBASE_SERVICE_ACCOUNT_KEY` | ❌ | - | Firebase 金鑰 JSON 字串 |
| `PYTORCH_CUDA_ALLOC_CONF` | ❌ | - | GPU 記憶體配置 |
| `LOG_LEVEL` | ❌ | INFO | 日誌級別 |

### 效能調整

#### GPU 配置

```bash
# 檢查 GPU 可用性
python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# GPU 記憶體優化
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# 使用特定 GPU
export CUDA_VISIBLE_DEVICES=0
```

#### CPU 優化

```bash
# 設置 PyTorch 執行緒數
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4

# 啟用優化
export TORCH_USE_CUDA_DSA=1
```

## 🐛 故障排除

### 常見問題

#### 1. **模型載入失敗**

**問題：** `OSError: Unable to load model`

**解決方案：**
```bash
# 檢查 HF Token
echo $HF_TOKEN

# 手動測試模型下載
python3 -c "
from huggingface_hub import HfApi
api = HfApi(token='your_token')
print(api.whoami())
"

# 確認模型權限
# 訪問模型頁面並接受使用條款
```

#### 2. **記憶體不足**

**問題：** `RuntimeError: CUDA out of memory`

**解決方案：**
```bash
# 調整批次大小
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:256

# 或強制使用 CPU
export CUDA_VISIBLE_DEVICES=""

# 減少並發處理
# 修改 main.py 中的 workers 數量
```

#### 3. **Firebase 連接錯誤**

**問題：** `FirebaseError: Permission denied`

**解決方案：**
```bash
# 檢查金鑰檔案
ls -la firebase-credentials.json

# 驗證 JSON 格式
python3 -c "import json; json.load(open('firebase-credentials.json'))"

# 測試連接
python3 -c "
import firebase_admin
from firebase_admin import credentials
cred = credentials.Certificate('firebase-credentials.json')
app = firebase_admin.initialize_app(cred)
print('✅ Firebase 連接成功')
"
```

#### 4. **端口佔用**

**問題：** `OSError: [Errno 48] Address already in use`

**解決方案：**
```bash
# 查找佔用進程
lsof -i :8000

# 終止進程
kill -9 <PID>

# 或使用不同端口
export PORT=8001
```

### 調試技巧

#### 1. **啟用詳細日誌**

```bash
export LOG_LEVEL=DEBUG
python3 main.py
```

#### 2. **檢查服務狀態**

```bash
# 健康檢查
curl http://localhost:8000/health

# 查看進程
ps aux | grep python

# 檢查端口
netstat -tulpn | grep 8000
```

#### 3. **測試音頻處理**

```bash
# 使用測試音頻
curl -X POST http://localhost:8000/upload \
  -F "file=@test.wav"

# 監控處理日誌
tail -f logs/app.log
```

## 📊 效能基準

### 硬體需求

| 配置 | CPU | 記憶體 | 處理速度 |
|------|-----|--------|----------|
| 最低 | 4核心 | 8GB | 5x 實時 |
| 建議 | 8核心 | 16GB | 3x 實時 |
| 高效能 | 16核心 + GPU | 32GB | 1.5x 實時 |

### 處理時間

- **10分鐘會議**: 2-5分鐘處理時間
- **30分鐘會議**: 5-15分鐘處理時間
- **60分鐘會議**: 10-30分鐘處理時間

*實際時間取決於音頻質量、說話者數量和硬體配置*

## 🔒 安全考量

### 網路安全

- **Cloudflare Tunnel**: 提供 TLS 加密和 DDoS 保護
- **無公網 IP**: 不直接暴露 Mac Mini 到互聯網
- **存取控制**: 可配置 IP 白名單和認證

### 資料安全

- **本地處理**: 音頻在本地設備處理
- **暫存清理**: 處理完成後自動清理暫存檔案
- **加密傳輸**: 所有網路傳輸使用 HTTPS

### 隱私保護

- **可選雲端**: Firebase 整合可選，支援純本地模式
- **資料控制**: 用戶完全控制音頻資料
- **透明處理**: 開源代碼，處理過程透明

## 📈 監控和維護

### 日誌管理

```bash
# 查看即時日誌
tail -f logs/app.log

# 日誌輪替
logrotate -f logrotate.conf

# 清理舊日誌
find logs/ -name "*.log.*" -mtime +7 -delete
```

### 效能監控

```bash
# 系統資源
top -p $(pgrep -f main.py)

# GPU 使用情況 (如果有)
nvidia-smi

# 記憶體使用
ps -p $(pgrep -f main.py) -o pid,vsz,rss,pcpu,pmem
```

### 自動重啟

```bash
# 創建 systemd 服務 (Linux)
sudo cp scripts/ai-meeting-processor.service /etc/systemd/system/
sudo systemctl enable ai-meeting-processor
sudo systemctl start ai-meeting-processor

# 或使用 launchd (macOS)
cp scripts/com.aimeetingtool.processor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.aimeetingtool.processor.plist
```

## 🚀 部署選項

### 本地開發

```bash
# 開發模式 - 支援熱重載
./start.sh dev
```

### 生產部署

```bash
# 生產模式 - 優化效能
./start.sh prod

# 或使用 Docker
docker build -t ai-meeting-processor .
docker run -p 8000:8000 -v $(pwd)/.env:/app/.env ai-meeting-processor
```

### 雲端部署

可以部署到：
- **AWS EC2** - GPU 實例支援
- **Google Cloud Compute** - TPU 加速
- **Azure VMs** - 自動擴展
- **本地伺服器** - 完全控制

## 📚 開發指南

### 程式碼結構

```
mac-processor/
├── main.py              # FastAPI 應用主程式
├── requirements.txt     # Python 依賴
├── .env.example        # 環境變數範本
├── start.sh            # 啟動腳本
├── tunnel.sh           # Tunnel 管理腳本
├── logs/               # 日誌目錄
├── temp/               # 暫存目錄
└── scripts/            # 工具腳本
```

### 添加新功能

1. **新增 API 端點**
```python
@app.post("/new-endpoint")
async def new_feature(request: NewRequest):
    # 實作新功能
    return {"result": "success"}
```

2. **添加依賴**
```bash
pip install new-package
pip freeze > requirements.txt
```

3. **更新文檔**
```bash
# 更新此 README
# 添加 API 文檔
# 更新範例
```

---

## 💡 最佳實踐

1. **資源管理**: 處理完成後立即清理暫存檔案
2. **錯誤處理**: 實作完整的異常捕獲和日誌記錄
3. **效能優化**: 根據硬體配置調整批次大小
4. **安全措施**: 定期更新依賴和安全檢查
5. **備份策略**: 重要配置檔案的備份

需要更多幫助？查看 [主要 README](../README.md) 或提交 [Issue](https://github.com/garyyang1001/aplay-ai-meeting-tool/issues)。
