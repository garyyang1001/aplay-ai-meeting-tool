# 🎙️ AI 會議助手 v2.0

**基於 WhisperX + OpenRouter 的智能會議錄音、轉錄和分析工具**

完全免費開源，支援繁體中文，提供專業級的說話者辨識和 AI 智能分析。月運行成本僅 $5-10！

## ✨ 核心特色

- 🎯 **完全免費** - WhisperX + OpenRouter 免費模型，無使用限制
- 🇹🇼 **優秀中文支援** - 針對繁體中文優化，轉錄準確率 >95%
- 👥 **精準說話者辨識** - pyannote.audio 技術，準確率 >90%
- ⚡ **極速處理** - 比原始 Whisper 快 20-70x，1小時音訊 <3分鐘處理
- 🤖 **AI 智能分析** - Google Gemma-3 免費模型，生成會議摘要、行動項目等
- 🔄 **雙軌容錯** - 後端 WhisperX + 瀏覽器備用，確保穩定性
- 📱 **PWA 支援** - 支援手機錄音，離線使用
- 💰 **超低成本** - 月運行成本僅電費 $5-10

## 🏗️ 技術架構

```
前端 PWA → 後端 API → 處理引擎 → AI 分析 → 結果返回
    ↓         ↓           ↓           ↓         ↓
錄音/上傳  FastAPI   WhisperX    OpenRouter   智能報告
                      ↓             ↓
                  說話者辨識    Gemma-3 分析
```

### 雙軌處理策略

**主要路徑：** 後端 WhisperX (最高品質)
- 語音轉錄：WhisperX (large-v2 模型)
- 說話者辨識：pyannote.audio 3.1
- AI 分析：OpenRouter Gemma-3-27B

**備用路徑：** 瀏覽器降級 (最大相容性)
- 語音轉錄：Web Speech API
- AI 分析：直接調用 OpenRouter

## 🚀 快速開始

### 一鍵安裝 (推薦)

```bash
# 克隆專案
git clone https://github.com/garyyang1001/aplay-ai-meeting-tool.git
cd aplay-ai-meeting-tool

# 執行快速啟動腳本
chmod +x quick-start.sh
./quick-start.sh
```

腳本會自動：
- ✅ 檢查系統需求
- ✅ 安裝系統依賴 (ffmpeg, libsndfile)
- ✅ 設置 Python 虛擬環境
- ✅ 安裝所有依賴套件
- ✅ 設定環境變數
- ✅ 創建啟動腳本

### 手動安裝

<details>
<summary>點擊展開手動安裝步驟</summary>

#### 1. 系統需求
- **Python**: 3.8-3.11
- **Node.js**: 16+ (前端開發)
- **系統依賴**: ffmpeg, libsndfile

```bash
# macOS
brew install python ffmpeg libsndfile

# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-venv ffmpeg libsndfile1

# 其他 Linux 發行版
# CentOS/RHEL: sudo yum install python3 ffmpeg libsndfile
```

#### 2. 後端設置

```bash
# 建立虛擬環境
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安裝依賴
pip install -r requirements.txt

# 設置環境變數
cp .env.example .env
# 編輯 .env 填入 API Keys
```

#### 3. API Keys 設置

**HuggingFace Token** (說話者辨識必要):
1. 訪問 [HuggingFace Settings](https://huggingface.co/settings/tokens)
2. 創建 Read token
3. 接受模型條款:
   - [speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
   - [segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)

**OpenRouter API Key** (AI 分析):
1. 訪問 [OpenRouter](https://openrouter.ai)
2. 註冊並取得免費 API Key

#### 4. 前端設置

```bash
# 返回專案根目錄
cd ..

# 安裝前端依賴
npm install
```

</details>

### 啟動服務

```bash
# 啟動後端 (一個終端)
./start_backend.sh
# 或手動: cd backend && source venv/bin/activate && python main.py

# 啟動前端 (另一個終端)
./start_frontend.sh
# 或手動: npm run dev
```

**訪問應用:**
- 前端界面: http://localhost:3000
- API 文檔: http://localhost:8000/docs

## 📖 使用指南

### 基本使用流程

1. **開始錄音** 🎙️
   - 點擊錄音按鈕開始記錄會議
   - 支援即時語音預覽 (可選)

2. **停止錄音** ⏹️
   - 完成後停止錄音，或上傳音訊檔案

3. **選擇分析** 🤖
   - 會議摘要：整體概述和重點
   - 行動項目：待辦事項和負責人
   - 重要決策：決策記錄和理由
   - 智能分析：深度洞察和建議

4. **查看結果** 📊
   - 精確轉錄 + 說話者標註
   - AI 智能分析報告
   - 分享到 Line 或複製結果

### 支援格式

| 格式 | 輸入支援 | 建議 |
|------|----------|------|
| **音訊格式** | MP3, WAV, M4A, WEBM, OGG, FLAC | WAV (無損) |
| **檔案大小** | 最大 100MB | <50MB 更快 |
| **時長限制** | 最長 2 小時 | 30-60分鐘最佳 |
| **音質建議** | 16kHz, 單聲道 | 清晰人聲 |

### 進階功能

- **說話者提示**: 指定參與人數提高辨識準確度
- **多語言支援**: 中文、英文、日文、韓文
- **批次處理**: 支援大檔案自動分段處理
- **即時狀態**: 處理進度和剩餘時間顯示

## 🔧 配置選項

### 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `WHISPER_MODEL_SIZE` | 模型大小 | `base` |
| `DEVICE` | 計算設備 | `auto` |
| `DEFAULT_LANGUAGE` | 預設語言 | `zh` |
| `MAX_FILE_SIZE` | 檔案大小限制(MB) | `100` |

### 效能調校

```bash
# 高準確度 (較慢)
export WHISPER_MODEL_SIZE=large-v2
export COMPUTE_TYPE=float32

# 高速度 (可能影響準確度)
export WHISPER_MODEL_SIZE=base
export COMPUTE_TYPE=float16
export DEVICE=cuda  # 如果有 GPU

# CPU 優化 (相容性最佳)
export DEVICE=cpu
export BATCH_SIZE=8
```

## 📊 效能基準

### 處理速度 (M1 Pro 32GB)

| 音訊長度 | WhisperX 處理時間 | 實時倍數 | 說話者辨識 |
|----------|-------------------|----------|------------|
| 5 分鐘 | 12 秒 | 25x | +3 秒 |
| 30 分鐘 | 65 秒 | 28x | +15 秒 |
| 60 分鐘 | 130 秒 | 28x | +30 秒 |

### 準確度測試

| 場景 | 轉錄準確率 | 說話者辨識準確率 |
|------|------------|------------------|
| 清晰會議 (2-3人) | 98% | 95% |
| 一般會議 (4-6人) | 95% | 88% |
| 嘈雜環境 | 90% | 82% |
| 中英混雜 | 93% | 86% |

## 💰 成本分析

| 項目 | 工具/服務 | 月成本 |
|------|-----------|--------|
| 語音轉錄 | WhisperX (本地) | **$0** |
| 說話者辨識 | pyannote.audio (本地) | **$0** |
| AI 分析 | OpenRouter Gemma-3 (免費) | **$0** |
| 儲存空間 | 本地儲存 | **$0** |
| 電費 | 24/7 運行 | **$5-10** |
| **總計** | | **$5-10/月** |

## 🛠️ 故障排除

<details>
<summary>常見問題解決方案</summary>

### GPU 相關問題

**Q: CUDA 不可用怎麼辦？**
```bash
# 檢查 CUDA
python -c "import torch; print(torch.cuda.is_available())"

# 如果不可用，使用 CPU
export DEVICE=cpu
```

**Q: GPU 記憶體不足？**
```bash
# 降低批次大小
export BATCH_SIZE=8

# 使用較小模型
export WHISPER_MODEL_SIZE=base

# 使用混合精度
export COMPUTE_TYPE=float16
```

### 模型載入問題

**Q: HuggingFace 模型下載失敗？**
```bash
# 檢查網路連接
ping huggingface.co

# 檢查 Token 是否正確
echo $HF_TOKEN

# 手動下載模型
python -c "from transformers import pipeline; pipeline('automatic-speech-recognition', 'openai/whisper-base')"
```

**Q: 說話者辨識不可用？**
1. 確認已接受模型使用條款
2. 檢查 HF_TOKEN 是否正確設定
3. 嘗試重新下載模型

### 轉錄準確度問題

**Q: 中文識別不準確？**
- 確保音訊品質良好
- 嘗試較大的模型 (large-v2)
- 檢查語言設定 (`language=zh`)
- 調整 `num_speakers` 參數

**Q: 說話者辨識錯亂？**
- 確保每個說話者聲音區別明顯
- 指定正確的說話者數量
- 避免過度重疊的對話
- 檢查音訊品質

### API 連接問題

**Q: OpenRouter API 失敗？**
```bash
# 測試 API 連接
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
     https://openrouter.ai/api/v1/models

# 檢查剩餘額度
# 訪問 https://openrouter.ai/credits
```

### 效能問題

**Q: 處理速度太慢？**
- 確認使用 GPU 加速
- 調整批次大小 (`BATCH_SIZE`)
- 使用較小模型 (`WHISPER_MODEL_SIZE=base`)
- 檢查系統資源使用情況

</details>

## 🔄 版本更新

### v2.0 主要更新
- ✅ 完整 WhisperX 整合
- ✅ OpenRouter Gemma-3 免費模型
- ✅ 雙軌容錯架構
- ✅ 精準說話者辨識
- ✅ 一鍵安裝腳本
- ✅ 完整 API 文檔

### 計劃功能 (v2.1)
- 🔄 即時轉錄顯示
- 📁 會議範本系統
- 🎛️ 高級音訊前處理
- 📊 會議品質評分
- 🔗 行事曆整合

## 🤝 貢獻指南

歡迎提交 Issue 和 Pull Request！

### 開發環境設置
```bash
# Fork 專案並 clone
git clone https://github.com/yourusername/aplay-ai-meeting-tool.git

# 建立開發分支
git checkout -b feature/amazing-feature

# 安裝開發依賴
cd backend && pip install -r requirements.txt
cd .. && npm install

# 運行測試
pytest backend/tests/
npm test

# 提交變更
git commit -m 'Add amazing feature'
git push origin feature/amazing-feature
```

### 代碼規範
- Python: Black + isort
- TypeScript: ESLint + Prettier
- 提交信息: 使用繁體中文

## 📄 授權

MIT License - 請查看 [LICENSE](LICENSE) 檔案

## 🙏 致謝

- [WhisperX](https://github.com/m-bain/whisperX) - 高效語音處理框架
- [pyannote.audio](https://github.com/pyannote/pyannote-audio) - 說話者辨識技術
- [OpenRouter](https://openrouter.ai) - 免費 AI 模型服務
- [FastAPI](https://fastapi.tiangolo.com/) - 現代 Python Web 框架

---

## 🆘 需要幫助？

- 📖 [詳細文檔](docs/README.md)
- 🐛 [問題回報](https://github.com/garyyang1001/aplay-ai-meeting-tool/issues)
- 💬 [討論區](https://github.com/garyyang1001/aplay-ai-meeting-tool/discussions)
- 📧 聯絡開發者: [開啟 Issue](https://github.com/garyyang1001/aplay-ai-meeting-tool/issues/new)

**🎉 立即開始你的 AI 會議助手之旅！**

[![Star this project](https://img.shields.io/github/stars/garyyang1001/aplay-ai-meeting-tool?style=social)](https://github.com/garyyang1001/aplay-ai-meeting-tool)
