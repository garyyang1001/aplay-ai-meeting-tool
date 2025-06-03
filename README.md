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

### 🌐 技術特色
- **繁體中文支援** - 完整的中文語音識別和分析
- **瀏覽器相容** - 支援 Chrome、Edge、Safari
- **即時處理** - 邊錄音邊轉文字
- **響應式設計** - 適配各種設備

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
- **樣式**: 原生 CSS3 with 動畫效果
- **部署**: Zeabur 雲端平台

## 🔧 專案結構

```
aplay-ai-meeting-tool/
├── src/
│   ├── main.ts          # 主要應用程式邏輯（包含語音功能）
│   ├── api.ts           # OpenRouter API 整合
│   └── vite-env.d.ts    # TypeScript 類型定義
├── index.html           # 主要 HTML 檔案（語音界面）
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
3. **即時轉文字** - 說話內容會即時顯示在轉錄區域
4. **停止錄音** - 再次點擊按鈕或點擊停止鍵
5. **選擇分析類型** - 選擇想要的 AI 分析角度
6. **開始分析** - AI 會自動分析錄音內容

### 文件上傳流程

1. **上傳音頻** - 點擊「上傳音頻文件」按鈕
2. **手動轉錄** - 目前需要手動輸入文字內容
3. **AI 分析** - 選擇分析類型並開始分析

## 🔑 API 設定

本專案使用 OpenRouter API 來存取 Google Gemma 3 模型：

- **模型**: `google/gemma-3-27b-it:free`
- **API 端點**: `https://openrouter.ai/api/v1/chat/completions`
- **認證**: Bearer Token (您的 API Key)

## 🚀 API 使用範例

```javascript
const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
  method: "POST",
  headers: {
    "Authorization": "Bearer <OPENROUTER_API_KEY>",
    "HTTP-Referer": "<YOUR_SITE_URL>",
    "X-Title": "阿玩AI語音會議分析工具",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    "model": "google/gemma-3-27b-it:free",
    "messages": [
      {
        "role": "user",
        "content": "請分析這個會議錄音轉錄內容..."
      }
    ]
  })
});
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

## 🐛 故障排除

### 語音功能問題
- **麥克風無權限**: 確認瀏覽器允許麥克風存取
- **語音識別失效**: 嘗試使用 Chrome 或 Edge 瀏覽器
- **錄音無聲**: 檢查系統音頻設定和麥克風

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

**享受您的 AI 驅動語音會議分析體驗！** 🎤🤖