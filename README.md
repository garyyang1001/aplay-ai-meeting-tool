# 🎤 阿玩AI語音會議分析工具

使用 Open Router API 和 Google Gemma 3 模型的 TypeScript Web 應用程式，專為會議語音錄製和智能分析而設計。

## ✨ 功能特色

### 🎙️ 語音錄製功能
- **即時錄音** - 一鍵開始/停止會議錄音
- **語音轉文字** - 自動將語音實時轉換為文字
- **音頻播放** - 可播放錄製的音頻文件
- **文件上傳** - 支援上傳現有音頻文件

### 🤖 AI 智能分析
- 📝 **會議摘要** - 自動生成會議重點摘要
- ✅ **行動項目** - 提取需要執行的任務清單
- 🎯 **重要決策** - 識別會議中的關鍵決定
- 📋 **後續追蹤** - 建議需要追蹤的事項
- 👥 **參與者分析** - 識別發言者和貢獻
- 😊 **情緒分析** - 分析會議整體氣氛

### 📱 分享功能
- **分享到Line** - 一鍵分享分析結果到Line
- **複製結果** - 快速複製分析內容到剪貼板
- **智能格式化** - 自動添加時間戳記和來源信息
- **長度優化** - 自動調整內容長度符合Line限制

### 🌐 技術特色
- **繁體中文支援** - 完整的中文語音識別和分析
- **手機優化設計** - 專為手機使用體驗優化
- **響應式佈局** - 適配各種設備尺寸
- **即時處理** - 邊錄音邊轉文字

## 🚀 快速開始

### 瀏覽器需求

**推薦瀏覽器**（支援語音功能）：
- Chrome 25+
- Edge 79+
- Safari 14.1+

**功能支援說明**：
- 🎤 語音錄製：需要麥克風權限
- 🗣️ 語音轉文字：需支援 Web Speech API
- 🤖 AI 分析：所有現代瀏覽器
- 📱 Line分享：支援手機和桌面版

### 環境需求

- Node.js 18+
- npm 或 yarn
- OpenRouter API Key ([申請連結](https://openrouter.ai/))

### 本地開發

1. **克隆專案**
   ```bash
   git clone https://github.com/garyyang1001/aplay-ai-meeting-tool.git
   cd aplay-ai-meeting-tool
   ```

2. **安裝依賴**
   ```bash
   npm install
   ```

3. **設定環境變數**
   ```bash
   cp .env.example .env
   # 編輯 .env 文件，填入您的 OpenRouter API Key
   ```

4. **啟動開發伺服器**
   ```bash
   npm run dev
   ```

5. **開啟瀏覽器**
   訪問 `http://localhost:3000`

### 📦 部署到 Zeabur

1. **連接 GitHub 儲存庫**
   - 登入 [Zeabur](https://zeabur.com/)
   - 選擇此 GitHub 儲存庫

2. **設定環境變數**
   在 Zeabur 專案設定中添加：
   ```
   VITE_OPENROUTER_API_KEY=your_actual_api_key_here
   ```

3. **部署**
   Zeabur 會自動檢測並部署您的應用程式

## 🛠 技術架構

- **前端框架**: Vanilla TypeScript + Vite
- **AI 模型**: Google Gemma 3 27B (透過 OpenRouter)
- **語音技術**: Web Speech API + MediaRecorder API
- **分享功能**: Line URL Scheme + Clipboard API
- **樣式**: 原生 CSS3 with 動畫效果
- **部署**: Zeabur 雲端平台

## 🔧 專案結構

```
aplay-ai-meeting-tool/
├── src/
│   ├── main.ts          # 主要應用程式邏輯（包含語音和分享功能）
│   ├── api.ts           # OpenRouter API 整合
│   └── vite-env.d.ts    # TypeScript 類型定義
├── index.html           # 主要 HTML 檔案（手機優化界面）
├── package.json         # 專案設定和依賴
├── tsconfig.json        # TypeScript 設定
├── vite.config.js       # Vite 建構設定
├── .env.example         # 環境變數範例
└── README.md           # 專案說明
```

## 🎯 使用方式

### 語音錄製流程

1. **授權麥克風** - 第一次使用時允許麥克風權限
2. **開始錄音** - 點擊大的紅色麥克風按鈕
3. **即時轉文字** - 說話內容會即時顯示在轉錄區域（固定高度，可滾動）
4. **停止錄音** - 再次點擊按鈕或點擊停止鍵
5. **選擇分析類型** - 選擇想要的 AI 分析角度
6. **開始分析** - AI 會自動分析錄音內容

### 分享功能流程

1. **完成AI分析** - 分析完成後會自動顯示分享按鈕
2. **選擇分享方式**：
   - **📱 分享到Line** - 自動打開Line應用程式或網頁版
   - **📋 複製結果** - 複製格式化後的內容到剪貼板
3. **自動格式化** - 包含分析類型、結果內容、時間戳記

### 文件上傳流程

1. **上傳音頻** - 點擊「上傳音頻文件」按鈕
2. **手動轉錄** - 目前需要手動輸入文字內容
3. **AI 分析** - 選擇分析類型並開始分析

## 📱 手機使用優化

### UI/UX 特色
- **固定高度轉錄框** - 避免內容過長影響版面
- **大尺寸按鈕** - 適合手指操作的按鈕大小
- **響應式設計** - 3個斷點適應不同螢幕
- **觸控反饋** - 按鈕點擊的視覺回饋

### 分享體驗
- **智能檢測** - 自動判斷手機/桌面環境
- **Line整合** - 手機直接打開Line app，桌面打開網頁版
- **內容優化** - 自動調整分享內容長度
- **一鍵操作** - 簡化分享流程

## 🔑 API 設定

本專案使用 OpenRouter API 來存取 Google Gemma 3 模型：

- **模型**: `google/gemma-3-27b-it:free`
- **API 端點**: `https://openrouter.ai/api/v1/chat/completions`
- **認證**: Bearer Token (您的 API Key)

## 📱 Line 分享技術（2025年6月更新）

### 分享機制
- **優先使用 Web Share API** - 在支援的裝置上使用原生分享功能
- **手機版備用方案**: 使用新版 Line URL Scheme (`https://line.me/R/share?text=`)
- **桌面版備用方案**: 使用 Line Social Plugins (`https://social-plugins.line.me/lineit/share?text=`)
- **內容格式**: 包含分析結果、時間戳記、來源標記

### 技術更新說明
- **修復舊版 API 失效問題** - 不再使用已棄用的 `line://msg/text/` 格式
- **改進編碼處理** - 確保 UTF-8 編碼正確處理中文字符
- **優化分享體驗** - 優先使用系統原生分享功能

### 分享內容範例
```
🤖 AI會議分析結果 - 會議摘要

本次會議主要討論了新產品功能開發計劃...

📅 分析時間：2025/6/3 下午8:17:58
🔗 使用工具：阿玩AI語音會議分析工具
```

## 🎤 語音功能技術細節

### 語音識別設定
- **語言**: 繁體中文 (zh-TW)
- **模式**: 連續識別 + 中間結果
- **引擎**: Web Speech API (webkitSpeechRecognition)

### 音頻錄製設定
- **格式**: WebM + Opus 編碼
- **採樣率**: 44.1kHz
- **處理**: 回音消除 + 噪音抑制

## 🔒 隱私與安全

- **本地處理**: 語音轉文字在瀏覽器本地進行
- **API 安全**: 所有 AI 分析透過加密連接
- **無儲存**: 錄音文件不會保存在伺服器
- **權限控制**: 需要明確的麥克風使用權限
- **分享安全**: 分享內容經過格式化和長度限制

## 🐛 故障排除

### 語音功能問題
- **麥克風無權限**: 確認瀏覽器允許麥克風存取
- **語音識別失效**: 嘗試使用 Chrome 或 Edge 瀏覽器
- **錄音無聲**: 檢查系統音頻設定和麥克風

### 分享功能問題
- **Line分享失敗**: 確認設備已安裝Line應用程式
- **複製失敗**: 檢查瀏覽器是否支援 Clipboard API
- **內容格式異常**: 確認分析結果完整生成

### API 問題
- **分析失敗**: 檢查 OpenRouter API Key 是否正確設定
- **網路錯誤**: 確認網路連接正常

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 授權

MIT License

## 👨‍💻 作者

Gary Yang - [GitHub](https://github.com/garyyang1001)

---

**享受您的 AI 驅動語音會議分析體驗！** 🎤🤖📱
