# AI 會議助手技術架構 v2.0

## 🎯 專案概述

基於 WhisperX 開源方案的 AI 會議助手，提供實時錄音、語音轉文字、說話者辨識和智能分析功能。

### 核心優勢
- ✅ **完全開源免費** - WhisperX + OpenRouter 免費模型
- ✅ **優秀中文支援** - WhisperX 對中文效果優於 pyannote.audio
- ✅ **一站式處理** - 整合轉錄和說話者辨識
- ✅ **極高性能** - 比原始 Whisper 快 60-70x
- ✅ **低成本運作** - 月成本 $0-5

## 🏗️ 系統架構

### 整體架構圖
```
手機 PWA → Firebase 儲存 → Mac Mini 處理 → OpenRouter 分析 → 結果回傳
    ↓           ↓              ↓                ↓              ↓
錄音上傳    音訊檔案       WhisperX 處理      AI 智能分析    前端顯示
                          (轉錄+說話者辨識)   (摘要+行動項目)
```

### 技術堆疊

#### 前端 (PWA)
- **框架**: Vanilla JavaScript + Web APIs
- **錄音**: MediaRecorder API
- **即時預覽**: Web Speech API (可選)
- **UI**: Tailwind CSS
- **部署**: Vercel/Netlify

#### 後端處理 (Mac Mini)
- **主框架**: FastAPI + Python
- **語音處理**: WhisperX (整合 Whisper + pyannote.audio)
- **任務隊列**: Celery + Redis
- **檔案處理**: FFmpeg

#### AI 分析
- **模型**: OpenRouter Gemma-3-27b-it (免費)
- **功能**: 會議摘要、行動項目、決策分析、智能洞察

#### 儲存
- **音訊檔案**: Firebase Storage
- **中繼資料**: Firebase Firestore
- **快取**: Redis

## 🔧 核心組件

### 1. WhisperX 處理器

```python
class WhisperXProcessor:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.batch_size = 16
        self.compute_type = "float16"
        
    def process_meeting_audio(self, audio_path, language="zh"):
        """完整處理：轉錄 + 說話者辨識"""
        
        # 1. 載入模型
        model = whisperx.load_model("large-v2", self.device)
        
        # 2. 轉錄
        audio = whisperx.load_audio(audio_path)
        result = model.transcribe(audio, batch_size=self.batch_size)
        
        # 3. 詞級對齊
        model_a, metadata = whisperx.load_align_model(language, self.device)
        result = whisperx.align(result["segments"], model_a, metadata, audio, self.device)
        
        # 4. 說話者辨識
        diarize_model = whisperx.DiarizationPipeline(device=self.device)
        diarize_segments = diarize_model(audio)
        result = whisperx.assign_word_speakers(diarize_segments, result)
        
        return result
```

### 2. OpenRouter 分析服務

```javascript
class OpenRouterService {
    constructor() {
        this.apiKey = process.env.OPENROUTER_API_KEY;
        this.baseURL = 'https://openrouter.ai/api/v1/chat/completions';
    }
    
    async analyzeTranscript(transcript, analysisType) {
        const prompts = {
            '會議摘要': '請提供詳細的會議摘要，包含主要議題、討論點、共識和未解決問題...',
            '行動項目': '請提取具體的行動項目、負責人、時程和優先順序...',
            '重要決策': '請列出所有決策，包含內容、理由、影響和執行方式...',
            '智能分析': '請提供全面分析：效率評估、參與度、討論深度、改善建議...'
        };
        
        const response = await fetch(this.baseURL, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: 'google/gemma-3-27b-it:free',
                messages: [{
                    role: 'user',
                    content: prompts[analysisType] + '\n\n' + this.formatTranscript(transcript)
                }]
            })
        });
        
        return (await response.json()).choices[0].message.content;
    }
}
```

### 3. PWA 前端控制器

```javascript
class MeetingRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
    }
    
    async startRecording() {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.mediaRecorder = new MediaRecorder(stream);
        
        this.mediaRecorder.ondataavailable = (e) => {
            this.audioChunks.push(e.data);
        };
        
        this.mediaRecorder.onstop = () => {
            this.processRecording();
        };
        
        this.mediaRecorder.start();
        this.isRecording = true;
    }
    
    async processRecording() {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
        
        // 1. 上傳到 Firebase
        const audioUrl = await this.uploadToFirebase(audioBlob);
        
        // 2. 發送到 Mac Mini 處理
        const transcriptResult = await this.sendToMacMini(audioUrl);
        
        // 3. OpenRouter 智能分析
        const analysis = await this.analyzeWithOpenRouter(transcriptResult);
        
        // 4. 顯示結果
        this.displayResults(transcriptResult, analysis);
    }
}
```

## 📊 性能指標

### 處理速度
- **轉錄速度**: 1小時音訊 < 5分鐘處理
- **說話者辨識**: 實時處理
- **AI 分析**: < 30秒
- **總處理時間**: < 6分鐘 (1小時音訊)

### 準確度
- **中文轉錄**: >95% (清晰語音)
- **說話者辨識**: >90% (2-6人會議)
- **時間戳精度**: 詞級 (±0.1秒)

## 💰 成本分析

| 項目 | 工具 | 月成本 |
|------|------|--------|
| 語音轉文字 | WhisperX (本地) | $0 |
| 說話者辨識 | 整合在 WhisperX | $0 |
| AI 分析 | OpenRouter Gemma-3 免費 | $0 |
| 檔案儲存 | Firebase 免費額度 | $0 |
| Mac Mini 電費 | 24/7 運行 | $5-10 |
| **總計** | | **$5-10/月** |

## 🔒 安全考量

### 資料隱私
- 音訊檔案可設置自動刪除
- 本地處理避免敏感資料外流
- Firebase 權限控制

### 系統安全
- Mac Mini 內網部署
- API 金鑰環境變數管理
- HTTPS 加密傳輸

## 🚀 擴展性

### 水平擴展
- 多台 Mac Mini 負載均衡
- Redis 集群
- CDN 加速檔案傳輸

### 功能擴展
- 多語言支援
- 情感分析
- 關鍵字提取
- 會議評分

## 📈 監控指標

### 系統監控
- CPU/GPU 使用率
- 記憶體消耗
- 處理隊列長度
- 錯誤率

### 業務監控
- 處理成功率
- 平均處理時間
- 用戶滿意度
- 功能使用統計