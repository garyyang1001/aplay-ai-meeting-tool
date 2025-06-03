# 🎙️ AI 會議助手

**基於 WhisperX + OpenRouter 的智能會議錄音、轉錄和分析工具**

完全免費開源，支援繁體中文，提供專業級的說話者辨識和 AI 智能分析。

## ✨ 核心特色

- 🎯 **完全免費** - WhisperX + OpenRouter 免費模型
- 🇹🇼 **優秀中文支援** - 針對繁體中文優化，轉錄準確率 >95%
- 👥 **精準說話者辨識** - pyannote.audio 技術，準確率 >90%
- ⚡ **極速處理** - 比原始 Whisper 快 20-70x
- 🤖 **AI 智能分析** - Google Gemma-3 免費模型
- 📱 **PWA 支援** - 支援手機錄音，離線使用

## 🚀 快速開始

### 1. 下載專案

```bash
git clone https://github.com/garyyang1001/aplay-ai-meeting-tool.git
cd aplay-ai-meeting-tool
```

### 2. 設置 API Keys

**HuggingFace Token** (必要)：
1. 前往：https://huggingface.co/settings/tokens
2. 創建 Read token
3. 接受模型條款：
   - https://huggingface.co/pyannote/speaker-diarization-3.1
   - https://huggingface.co/pyannote/segmentation-3.0

**OpenRouter API Key** (必要)：
1. 前往：https://openrouter.ai/keys
2. 註冊並創建免費 API Key

### 3. 啟動服務

#### 啟動後端（第一個終端）
```bash
cd backend
chmod +x start.sh
./start.sh
```

第一次執行會：
- ✅ 自動創建 Python 虛擬環境
- ✅ 安裝所有依賴套件
- ✅ 創建 .env 設定檔
- ⚠️ 提示你填入 API Keys

編輯 `backend/.env` 填入你的 API Keys，然後重新執行 `./start.sh`

#### 啟動前端（第二個終端）
```bash
chmod +x start_frontend.sh
./start_frontend.sh
```

### 4. 開始使用

- 🌐 **前端界面**: http://localhost:3000
- 📚 **API 文檔**: http://localhost:8000/docs

## 📱 使用流程

1. **錄音** 🎙️ - 點擊錄音按鈕開始記錄會議
2. **處理** ⚡ - 自動進行語音轉錄和說話者辨識
3. **分析** 🤖 - 選擇 AI 分析類型：
   - 會議摘要
   - 行動項目
   - 重要決策
   - 智能分析
4. **結果** 📊 - 查看轉錄結果和 AI 分析報告

## 🔧 系統需求

- **Python**: 3.8-3.11
- **Node.js**: 16+
- **系統依賴**: 
  ```bash
  # macOS
  brew install ffmpeg libsndfile
  
  # Ubuntu/Debian  
  sudo apt install ffmpeg libsndfile1
  ```

## 💰 成本

| 項目 | 月成本 |
|------|--------|
| 語音轉錄 (WhisperX 本地) | **$0** |
| 說話者辨識 (pyannote 本地) | **$0** |
| AI 分析 (OpenRouter 免費) | **$0** |
| 電費 (24/7 運行) | **$5-10** |
| **總計** | **$5-10/月** |

## 🛠️ 故障排除

### 環境變數錯誤
```bash
# 確保 .env 文件格式正確
cat backend/.env

# 手動載入環境變數
cd backend
source .env
python main.py
```

### 端口佔用
```bash
# 停止佔用端口的進程
sudo kill -9 $(lsof -t -i:8000)

# 或使用不同端口
PORT=8001 python backend/main.py
```

### 套件安裝問題
```bash
# 重新安裝虛擬環境
cd backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### GPU 問題
```bash
# 強制使用 CPU
echo "DEVICE=cpu" >> backend/.env
echo "COMPUTE_TYPE=float32" >> backend/.env
```

## 🤝 獲得幫助

- 🐛 [問題回報](https://github.com/garyyang1001/aplay-ai-meeting-tool/issues)
- 💬 [討論區](https://github.com/garyyang1001/aplay-ai-meeting-tool/discussions)

## 📄 授權

MIT License - 請查看 [LICENSE](LICENSE) 檔案

---

**🎉 開始你的 AI 會議助手之旅！**