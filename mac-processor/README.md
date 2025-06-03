# 🖥️ Mac Mini 音頻處理服務

> 專業級音頻處理和說話者識別服務

## 🎯 功能特色

- ✅ **專業說話者識別** - 使用 pyannote.audio 3.1.1 模型
- ✅ **多格式音頻支援** - 支援 WAV、MP3、WebM 等格式
- ✅ **RESTful API** - 完整的 FastAPI 接口
- ✅ **Firebase 整合** - 自動同步處理結果
- ✅ **背景處理** - 非阻塞式異步處理

## 🚀 快速開始

### 📋 系統需求

- **Python**: 3.8 或更高版本
- **記憶體**: 建議 8GB 以上
- **儲存**: 至少 5GB 可用空間
- **網路**: 穩定網際網路連接

### ⚡ 快速安裝

```bash
# 進入 mac-processor 目錄
cd mac-processor

# 執行一鍵啟動腳本
chmod +x start.sh
./start.sh
```

### 🔧 手動安裝

```bash
# 1. 創建虛擬環境
python3 -m venv venv
source venv/bin/activate

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 設置環境變數
cp .env.example .env
nano .env  # 設置 HF_TOKEN

# 4. 啟動服務
python main.py
```

## 🔑 環境配置

### 必要配置

```bash
# Hugging Face Token（必須）
HF_TOKEN=your_huggingface_token_here

# 服務配置
PORT=8000
HOST=0.0.0.0
```

### Hugging Face 設置

1. 訪問 [Hugging Face Settings](https://huggingface.co/settings/tokens)
2. 創建新的 Access Token
3. 接受模型使用條款：
   - [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
   - [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)

## 🔗 Cloudflare Tunnel 設置

```bash
# 安裝 cloudflared
./tunnel.sh install

# 啟動快速 tunnel
./tunnel.sh quick

# 複製輸出的 URL 到前端 .env 文件
```

## 📡 API 參考

### 核心端點

- `GET /` - 健康檢查
- `GET /health` - 詳細健康檢查
- `POST /process` - 處理音頻請求
- `GET /status/{job_id}` - 查詢處理狀態
- `POST /upload` - 直接上傳音頻檔案

### 使用範例

```bash
# 健康檢查
curl http://localhost:8000/health

# 處理音頻
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-123",
    "audio_url": "https://example.com/audio.wav",
    "num_speakers": 2
  }'

# 查詢狀態
curl http://localhost:8000/status/test-123
```

## 🐛 故障排除

### 常見問題

**Q: 服務啟動失敗**
- 檢查 Python 版本（3.8+）
- 確認虛擬環境啟動
- 重新安裝依賴

**Q: pyannote 模型載入失敗**
- 確認 HF_TOKEN 正確
- 檢查模型使用條款接受狀態
- 確認網路連接

**Q: Cloudflare Tunnel 無法連接**
- 檢查本地服務是否運行
- 重新啟動 tunnel

### 調試模式

```bash
# 啟用調試
export LOG_LEVEL=DEBUG
python main.py
```

## 📈 效能優化

### 效能指標
- **初始載入**: 30-60秒
- **處理速度**: 約 0.5-2x 即時速度
- **記憶體使用**: 3-6GB

### 優化建議
```bash
# GPU 加速（如果可用）
export CUDA_VISIBLE_DEVICES=0

# 記憶體優化
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

## 📞 技術支援

- **專案**: [GitHub Repository](https://github.com/garyyang1001/aplay-ai-meeting-tool)
- **問題回報**: [GitHub Issues](https://github.com/garyyang1001/aplay-ai-meeting-tool/issues)
- **pyannote 文檔**: [pyannote.github.io](https://pyannote.github.io/)
