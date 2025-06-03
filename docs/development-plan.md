# 開發計畫 v2.0 - WhisperX 方案

## 📅 總時程：2週完成 MVP

### Week 1: 核心功能實作

#### Day 1-2: Mac Mini 環境設置

**環境準備**
```bash
# 1. 安裝 Python 環境
python3 -m venv whisperx-env
source whisperx-env/bin/activate

# 2. 安裝 WhisperX
pip install whisperx
# 或最新版本
pip install git+https://github.com/m-bain/whisperx.git

# 3. 安裝其他依賴
pip install fastapi uvicorn redis celery
pip install firebase-admin

# 4. 設置 HuggingFace Token
export HF_TOKEN="your_huggingface_token"

# 5. 測試 GPU 支援
python -c "import torch; print(torch.cuda.is_available())"
```

**測試 WhisperX**
```python
# test_whisperx.py
import whisperx

# 測試基本功能
device = "cuda" if torch.cuda.is_available() else "cpu"
model = whisperx.load_model("base", device)
audio = whisperx.load_audio("test_audio.wav")
result = model.transcribe(audio)
print(result["segments"])
```

#### Day 3-4: 後端 API 開發

**FastAPI 服務結構**
```
backend/
├── main.py              # FastAPI 主程式
├── processors/
│   ├── __init__.py
│   ├── whisperx_processor.py  # WhisperX 處理器
│   └── openrouter_client.py   # OpenRouter 客戶端
├── models/
│   ├── __init__.py
│   └── schemas.py       # 資料模型
├── utils/
│   ├── __init__.py
│   ├── firebase_client.py     # Firebase 整合
│   └── file_handler.py        # 檔案處理
├── workers/
│   ├── __init__.py
│   └── celery_tasks.py        # 背景任務
└── requirements.txt
```

**核心 API 端點**
```python
# main.py
from fastapi import FastAPI, UploadFile, BackgroundTasks
from processors.whisperx_processor import WhisperXProcessor
from processors.openrouter_client import OpenRouterClient

app = FastAPI(title="AI Meeting Tool Backend")
processor = WhisperXProcessor()
openrouter = OpenRouterClient()

@app.post("/process-audio")
async def process_audio(
    file: UploadFile,
    language: str = "zh",
    analysis_type: str = "會議摘要",
    background_tasks: BackgroundTasks = None
):
    """處理上傳的音訊檔案"""
    
    # 1. 保存檔案
    audio_path = await save_uploaded_file(file)
    
    # 2. WhisperX 處理
    transcript_result = processor.process_meeting_audio(audio_path, language)
    
    # 3. OpenRouter 分析
    analysis = await openrouter.analyze_transcript(
        transcript_result["segments"], 
        analysis_type
    )
    
    return {
        "status": "completed",
        "transcript": transcript_result["segments"],
        "speaker_count": len(set(seg.get("speaker", "UNKNOWN") for seg in transcript_result["segments"])),
        "word_segments": transcript_result.get("word_segments", []),
        "analysis": analysis,
        "processing_time": "實際測量時間"
    }

@app.post("/analyze-transcript")
async def analyze_transcript(
    transcript: list,
    analysis_type: str
):
    """分析已有的轉錄文字"""
    analysis = await openrouter.analyze_transcript(transcript, analysis_type)
    return {"analysis": analysis}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "whisperx": "ready"}
```

#### Day 5-6: 前端 PWA 更新

**更新錄音處理流程**
```javascript
// src/recorder.js
class MeetingRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.macMiniUrl = 'http://your-mac-mini-ip:8000';
    }
    
    async startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });
            
            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });
            
            this.mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    this.audioChunks.push(e.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                this.processRecording();
            };
            
            this.mediaRecorder.start(1000); // 每秒收集一次資料
            this.isRecording = true;
            this.updateUI('recording');
            
        } catch (error) {
            console.error('錄音失敗:', error);
            this.showError('無法存取麥克風，請檢查權限設定');
        }
    }
    
    async stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            this.updateUI('processing');
        }
    }
    
    async processRecording() {
        try {
            // 1. 建立音訊 Blob
            const audioBlob = new Blob(this.audioChunks, { 
                type: 'audio/webm;codecs=opus' 
            });
            
            // 2. 顯示處理狀態
            this.updateProcessingStep('uploading');
            
            // 3. 上傳到 Mac Mini 處理
            const formData = new FormData();
            formData.append('file', audioBlob, 'recording.webm');
            formData.append('language', 'zh');
            formData.append('analysis_type', this.getSelectedAnalysisType());
            
            const response = await fetch(`${this.macMiniUrl}/process-audio`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`處理失敗: ${response.statusText}`);
            }
            
            this.updateProcessingStep('analyzing');
            
            const result = await response.json();
            
            // 4. 顯示結果
            this.displayResults(result);
            
            // 5. 清理
            this.audioChunks = [];
            
        } catch (error) {
            console.error('處理錯誤:', error);
            this.showError('處理音訊時發生錯誤，請重試');
        }
    }
    
    getSelectedAnalysisType() {
        const selectedBtn = document.querySelector('.analysis-btn.selected');
        return selectedBtn ? selectedBtn.dataset.type : '會議摘要';
    }
    
    displayResults(result) {
        const resultsPanel = document.getElementById('resultsPanel');
        const resultContent = document.getElementById('resultContent');
        
        // 顯示轉錄結果
        let transcriptHtml = '<h4>會議轉錄</h4><div class="transcript">';
        result.transcript.forEach(segment => {
            const speaker = segment.speaker || 'UNKNOWN';
            const text = segment.text;
            const start = segment.start.toFixed(1);
            
            transcriptHtml += `
                <div class="segment">
                    <span class="timestamp">[${start}s]</span>
                    <span class="speaker">${speaker}:</span>
                    <span class="text">${text}</span>
                </div>
            `;
        });
        transcriptHtml += '</div>';
        
        // 顯示分析結果
        const analysisHtml = `
            <h4>智能分析</h4>
            <div class="analysis">
                ${result.analysis.replace(/\n/g, '<br>')}
            </div>
        `;
        
        // 顯示統計資訊
        const statsHtml = `
            <h4>會議統計</h4>
            <div class="stats">
                <p>參與人數: ${result.speaker_count}</p>
                <p>處理時間: ${result.processing_time}</p>
            </div>
        `;
        
        resultContent.innerHTML = transcriptHtml + analysisHtml + statsHtml;
        
        // 切換顯示
        document.getElementById('processingPanel').classList.add('hidden');
        resultsPanel.classList.remove('hidden');
    }
}
```

#### Day 7: 整合測試

**端對端測試**
- 錄音功能測試
- 上傳處理測試
- 轉錄準確度測試
- 說話者辨識測試
- AI 分析品質測試

### Week 2: 優化與部署

#### Day 8-9: 效能優化

**Mac Mini 優化**
```python
# 效能監控
class PerformanceMonitor:
    def __init__(self):
        self.metrics = []
    
    def track_processing_time(self, audio_duration, processing_time):
        ratio = processing_time / audio_duration
        self.metrics.append({
            'timestamp': datetime.now(),
            'audio_duration': audio_duration,
            'processing_time': processing_time,
            'real_time_factor': ratio
        })
        
        # 目標：Real-time factor < 0.1 (10倍速度)
        if ratio > 0.1:
            logger.warning(f"處理速度較慢: {ratio:.2f}x")
```

**記憶體優化**
```python
# 批次處理大檔案
def process_large_audio(audio_path, chunk_size=30):
    """分塊處理大型音訊檔案"""
    audio = whisperx.load_audio(audio_path)
    total_duration = len(audio) / 16000  # 假設 16kHz
    
    results = []
    for start in range(0, int(total_duration), chunk_size):
        end = min(start + chunk_size, total_duration)
        chunk = audio[start*16000:end*16000]
        
        chunk_result = model.transcribe(chunk)
        # 調整時間戳
        for segment in chunk_result["segments"]:
            segment["start"] += start
            segment["end"] += start
        
        results.extend(chunk_result["segments"])
        
        # 清理記憶體
        del chunk
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
    
    return {"segments": results}
```

#### Day 10-11: 部署與監控

**系統服務設置**
```bash
# systemd 服務檔案
sudo tee /etc/systemd/system/whisperx-api.service > /dev/null <<EOF
[Unit]
Description=WhisperX API Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/backend
Environment=HF_TOKEN=your_token
Environment=OPENROUTER_API_KEY=your_key
ExecStart=/path/to/whisperx-env/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable whisperx-api
sudo systemctl start whisperx-api
```

**監控設置**
```python
# 簡單監控腳本
import psutil
import requests
from datetime import datetime

def monitor_system():
    # CPU 使用率
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # 記憶體使用
    memory = psutil.virtual_memory()
    
    # GPU 使用（如果有）
    gpu_stats = get_gpu_stats() if torch.cuda.is_available() else None
    
    # API 健康檢查
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        api_status = response.status_code == 200
    except:
        api_status = False
    
    stats = {
        'timestamp': datetime.now().isoformat(),
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'api_healthy': api_status,
        'gpu_stats': gpu_stats
    }
    
    # 記錄到檔案或發送警報
    log_stats(stats)
    
    return stats
```

#### Day 12-13: 使用者測試

**測試案例**
1. 單人簡報錄音
2. 2-3人小型會議
3. 4-6人大型會議
4. 中英混雜語音
5. 背景噪音環境

**品質評估指標**
- 轉錄準確率 >95%
- 說話者辨識準確率 >90%
- 處理速度 <0.1x 實時
- AI 分析相關性 >85%

#### Day 14: 文檔完善與發布

**完成項目**
- ✅ 技術文檔
- ✅ 使用手冊
- ✅ 部署指南
- ✅ 故障排除
- ✅ 效能調校指南

## 🎯 里程碑檢核

### Week 1 結束檢核
- [ ] Mac Mini 環境就緒
- [ ] WhisperX 正常運作
- [ ] FastAPI 後端完成
- [ ] PWA 前端更新
- [ ] 基本功能端對端測試通過

### Week 2 結束檢核
- [ ] 效能達標（<0.1x 實時處理）
- [ ] 系統服務穩定運行
- [ ] 監控告警正常
- [ ] 使用者測試通過
- [ ] 文檔完整

## 🚨 風險管控

### 技術風險
- **GPU 記憶體不足**: 調整 batch_size 和 compute_type
- **中文辨識準確率**: 測試不同模型大小
- **網路連線問題**: 實作斷線重試機制

### 進度風險
- **依賴套件衝突**: 提前測試相容性
- **硬體效能不足**: 準備降級方案
- **第三方服務中斷**: 實作備用方案

## 📈 後續擴展

### Phase 2 功能 (Week 3-4)
- 即時轉錄顯示
- 多語言自動偵測
- 會議範本和客製化提示
- 批次處理多個檔案

### Phase 3 功能 (Month 2)
- 情感分析
- 關鍵字提取
- 會議評分系統
- 整合行事曆

### Phase 4 功能 (Month 3)
- 多人協作
- 權限管理
- 資料分析儀表板
- API 開放給第三方