# 🤖 阿玩AI會議工具

使用 Open Router API 和 Google Gemma 3 模型的 TypeScript Web 應用程式，專為會議內容分析而設計。

## ✨ 功能特色

- 📝 **會議摘要** - 自動生成會議重點摘要
- ✅ **行動項目** - 提取需要執行的任務清單
- 🎯 **重要決策** - 識別會議中的關鍵決定
- 📋 **後續追蹤** - 建議需要追蹤的事項
- 🎨 **自定義分析** - 支援自定義分析角度
- 🌐 **繁體中文支援** - 完整的中文界面和回應

## 🚀 快速開始

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
- **樣式**: 原生 CSS3 with Flexbox
- **部署**: Zeabur 雲端平台

## 🔧 專案結構

```
aplay-ai-meeting-tool/
├── src/
│   ├── main.ts          # 主要應用程式邏輯
│   └── api.ts           # OpenRouter API 整合
├── index.html           # 主要 HTML 檔案
├── package.json         # 專案設定和依賴
├── tsconfig.json        # TypeScript 設定
├── vite.config.js       # Vite 建構設定
├── .env.example         # 環境變數範例
└── README.md           # 專案說明
```

## 🎯 使用方式

1. **輸入會議內容** - 在文字區域貼上或輸入會議記錄
2. **選擇分析類型** - 從下拉選單選擇想要的分析角度
3. **點擊分析** - AI 會在幾秒內提供詳細分析
4. **查看結果** - 結果會以易讀的格式顯示

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
    "X-Title": "阿玩AI會議工具",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    "model": "google/gemma-3-27b-it:free",
    "messages": [
      {
        "role": "user",
        "content": "請分析這個會議內容..."
      }
    ]
  })
});
```

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 授權

MIT License

## 👨‍💻 作者

Gary Yang - [GitHub](https://github.com/garyyang1001)

---

**享受您的 AI 驅動會議分析體驗！** 🚀
