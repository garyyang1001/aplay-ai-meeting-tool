import { OpenRouterAPI } from './api';

// 全域變數
let api: OpenRouterAPI;
let mediaRecorder: MediaRecorder | null = null;
let audioStream: MediaStream | null = null;
let recordingStartTime: number = 0;
let recordingTimer: NodeJS.Timeout | null = null;
let recognition: any = null; // 使用 any 避免類型問題
let isRecording = false;
let transcriptText = '';

// 初始化
function init() {
    console.log('阿玩AI語音會議分析工具啟動中...');
    
    // 檢查環境變數
    const apiKey = (import.meta as any).env.VITE_OPENROUTER_API_KEY as string;
    if (!apiKey) {
        showStatus('警告：未設定 OpenRouter API Key', 'error');
        return;
    }
    
    api = new OpenRouterAPI(apiKey);
    
    // 檢查瀏覽器支援
    checkBrowserSupport();
    
    // 初始化語音識別
    initSpeechRecognition();
    
    showStatus('系統已就緒 - 可以開始錄音');
}

function checkBrowserSupport() {
    let supportStatus = [];
    
    // 檢查 MediaRecorder 支援
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        supportStatus.push('不支援麥克風錄音');
    }
    
    // 檢查語音識別支援
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
        supportStatus.push('不支援語音識別');
    }
    
    if (supportStatus.length > 0) {
        showStatus(`瀏覽器限制：${supportStatus.join(', ')}`, 'error');
    }
}

function initSpeechRecognition() {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'zh-TW'; // 設定為繁體中文
        
        recognition.onresult = (event: any) => {
            let finalTranscript = '';
            let interimTranscript = '';
            
            for (let i = event.results.length - 1; i >= 0; i--) {
                const result = event.results[i];
                if (result.isFinal) {
                    finalTranscript = result[0].transcript + finalTranscript;
                } else {
                    interimTranscript = result[0].transcript + interimTranscript;
                }
            }
            
            updateTranscript(finalTranscript, interimTranscript);
        };
        
        recognition.onerror = (event: any) => {
            console.error('語音識別錯誤:', event.error);
            showStatus(`語音識別錯誤: ${event.error}`, 'error');
        };
        
        recognition.onend = () => {
            if (isRecording) {
                // 如果還在錄音，重新啟動語音識別
                try {
                    recognition?.start();
                } catch (e) {
                    console.log('語音識別重啟失敗:', e);
                }
            }
        };
    }
}

function updateTranscript(finalText: string, interimText: string) {
    const transcriptElement = document.getElementById('transcript');
    if (transcriptElement) {
        if (finalText) {
            transcriptText += finalText + ' ';
        }
        transcriptElement.textContent = transcriptText + (interimText ? `[${interimText}]` : '');
    }
}

// 錄音控制函數
async function toggleRecording() {
    if (isRecording) {
        await stopRecording();
    } else {
        await startRecording();
    }
}

async function startRecording() {
    try {
        // 請求麥克風權限
        audioStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 44100
            }
        });
        
        // 初始化 MediaRecorder
        const options = { mimeType: 'audio/webm;codecs=opus' };
        try {
            mediaRecorder = new MediaRecorder(audioStream, options);
        } catch (e) {
            mediaRecorder = new MediaRecorder(audioStream);
        }
        
        const audioChunks: Blob[] = [];
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            const audioUrl = URL.createObjectURL(audioBlob);
            
            const audioPlayer = document.getElementById('audioPlayer') as HTMLAudioElement;
            if (audioPlayer) {
                audioPlayer.src = audioUrl;
                audioPlayer.style.display = 'block';
            }
        };
        
        // 開始錄音
        mediaRecorder.start(1000); // 每秒收集一次數據
        isRecording = true;
        recordingStartTime = Date.now();
        
        // 開始語音識別
        if (recognition) {
            transcriptText = '';
            try {
                recognition.start();
            } catch (e) {
                console.error('語音識別啟動失敗:', e);
            }
        }
        
        // 更新 UI
        updateRecordingUI(true);
        startRecordingTimer();
        
        showStatus('正在錄音中...');
        
    } catch (error) {
        console.error('錄音啟動失敗:', error);
        showStatus('錄音啟動失敗，請檢查麥克風權限', 'error');
    }
}

async function stopRecording() {
    if (!isRecording) return;
    
    isRecording = false;
    
    // 停止錄音
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
    }
    
    // 停止語音識別
    if (recognition) {
        try {
            recognition.stop();
        } catch (e) {
            console.log('語音識別停止失敗:', e);
        }
    }
    
    // 停止音頻流
    if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
        audioStream = null;
    }
    
    // 更新 UI
    updateRecordingUI(false);
    stopRecordingTimer();
    
    showStatus('錄音完成');
}

function updateRecordingUI(recording: boolean) {
    const recordBtn = document.getElementById('recordBtn');
    const stopBtn = document.getElementById('stopBtn');
    const recordingSection = document.getElementById('recordingSection');
    const recordingStatus = document.getElementById('recordingStatus');
    
    if (recording) {
        recordBtn?.classList.add('recording');
        if (stopBtn) stopBtn.style.display = 'inline-block';
        recordingSection?.classList.add('recording');
        if (recordingStatus) recordingStatus.textContent = '🔴 錄音中...';
    } else {
        recordBtn?.classList.remove('recording');
        if (stopBtn) stopBtn.style.display = 'none';
        recordingSection?.classList.remove('recording');
        if (recordingStatus) recordingStatus.textContent = '點擊麥克風開始錄製會議';
    }
}

function startRecordingTimer() {
    recordingTimer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        
        const recordingTime = document.getElementById('recordingTime');
        if (recordingTime) {
            recordingTime.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
    }, 1000);
}

function stopRecordingTimer() {
    if (recordingTimer) {
        clearInterval(recordingTimer);
        recordingTimer = null;
    }
    
    const recordingTime = document.getElementById('recordingTime');
    if (recordingTime) {
        recordingTime.textContent = '00:00';
    }
}

// 文件上傳處理
function handleFileUpload(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (file) {
        const audioUrl = URL.createObjectURL(file);
        const audioPlayer = document.getElementById('audioPlayer') as HTMLAudioElement;
        if (audioPlayer) {
            audioPlayer.src = audioUrl;
            audioPlayer.style.display = 'block';
        }
        
        const transcript = document.getElementById('transcript');
        if (transcript) {
            transcript.textContent = '已上傳音頻文件，請手動輸入轉錄文字或使用其他語音轉文字服務';
        }
        
        showStatus('音頻文件已上傳');
    }
}

// AI 分析功能
async function analyzeTranscript() {
    const transcript = document.getElementById('transcript')?.textContent?.trim();
    const analysisTypeElement = document.getElementById('analysisType') as HTMLSelectElement;
    const analyzeBtn = document.getElementById('analyzeBtn') as HTMLButtonElement;
    
    if (!transcript || transcript === '等待錄音...' || transcript.includes('已上傳音頻文件')) {
        showResult('請先錄音或確保語音轉文字完成', true);
        return;
    }
    
    if (!api) {
        showResult('API 未初始化，請檢查設定', true);
        return;
    }
    
    const analysisType = analysisTypeElement.value;
    
    // 顯示載入狀態
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = '🤔 AI思考中...';
    showStatus('正在分析中，請稍候...');
    showResult('<div class=\"loading\">⏳ AI正在分析您的會議內容...</div>');
    
    try {
        const prompt = getPromptTemplate(analysisType);
        const fullPrompt = `${prompt}\n\n會議錄音轉錄內容：\n${transcript}`;
        
        const response = await api.chat(fullPrompt);
        
        showResult(response);
        showStatus('分析完成！');
        
    } catch (error) {
        console.error('分析錯誤:', error);
        showResult(`分析失敗：${error instanceof Error ? error.message : '未知錯誤'}`, true);
        showStatus('分析失敗', 'error');
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = '🤖 開始AI分析';
    }
}

function getPromptTemplate(type: string): string {
    const templates = {
        summary: '請為以下會議錄音轉錄內容提供一個簡潔明確的摘要，包含主要討論點和結論：',
        action_items: '請從以下會議錄音轉錄內容中提取出所有需要執行的行動項目，包含負責人和時間點：',
        key_decisions: '請列出以下會議錄音轉錄內容中做出的所有重要決策和決定：',
        follow_up: '請分析以下會議錄音轉錄內容，並建議需要後續追蹤的事項和時間點：',
        participants: '請分析以下會議錄音轉錄內容，識別參與者並總結各人的主要觀點和貢獻：',
        sentiment: '請分析以下會議錄音轉錄內容的整體情緒和氣氛，包含正面、負面或中性的討論：'
    };
    
    return templates[type as keyof typeof templates] || templates.summary;
}

function showStatus(message: string, type: 'success' | 'error' | 'info' = 'info') {
    const status = document.getElementById('status');
    if (status) {
        status.textContent = message;
        status.className = `status ${type}`;
    }
}

function showResult(content: string, isError: boolean = false) {
    const result = document.getElementById('result');
    if (result) {
        result.innerHTML = isError ? 
            `<div class=\"error\">${content}</div>` : 
            `<div>${content.replace(/\n/g, '<br>')}</div>`;
        result.style.display = 'block';
    }
}

// 綁定全域函數
(window as any).toggleRecording = toggleRecording;
(window as any).stopRecording = stopRecording;
(window as any).handleFileUpload = handleFileUpload;
(window as any).analyzeTranscript = analyzeTranscript;

// 當 DOM 載入完成時初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}