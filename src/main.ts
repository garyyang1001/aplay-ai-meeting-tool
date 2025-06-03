import enhancedRecorder from './enhanced-recorder';
import type { ProcessingResult } from './enhanced-recorder';

// 全域狀態
let currentResult: ProcessingResult | null = null;
let isProcessing = false;

/**
 * 初始化應用程式
 */
function init() {
    console.log('🚀 AI 會議工具 v2.0 啟動中...');
    
    // 設置狀態回調
    enhancedRecorder.setStatusCallback(showStatus);
    
    // 檢查瀏覽器支援
    checkBrowserSupport();
    
    // 檢查服務狀態
    checkServiceStatus();
    
    showStatus('系統已就緒 - 可以開始錄音', 'success');
}

/**
 * 檢查瀏覽器支援
 */
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
    
    // 檢查 Firebase 支援
    if (!('indexedDB' in window)) {
        supportStatus.push('不支援離線存儲');
    }
    
    if (supportStatus.length > 0) {
        showStatus(`瀏覽器限制：${supportStatus.join(', ')}`, 'warning');
    } else {
        showStatus('瀏覽器功能檢查通過', 'success');
    }
}

/**
 * 檢查服務狀態
 */
async function checkServiceStatus() {
    const status = enhancedRecorder.getStatus();
    
    const statusElement = document.getElementById('serviceStatus');
    if (statusElement) {
        const statusHTML = `
            <div class="service-status">
                <div class="status-item ${status.firebaseAvailable ? 'available' : 'unavailable'}">
                    <span class="status-icon">${status.firebaseAvailable ? '✅' : '❌'}</span>
                    <span>Firebase: ${status.firebaseAvailable ? '已連接' : '未連接'}</span>
                </div>
                <div class="status-item ${status.macMiniStatus.available ? 'available' : 'unavailable'}">
                    <span class="status-icon">${status.macMiniStatus.available ? '✅' : '❌'}</span>
                    <span>Mac Mini: ${status.macMiniStatus.available ? '已連接' : '未連接'}</span>
                </div>
                <div class="processing-mode">
                    <span class="mode-label">處理模式:</span>
                    <span class="mode-value">${getProcessingMode(status)}</span>
                </div>
            </div>
        `;
        statusElement.innerHTML = statusHTML;
    }
}

/**
 * 獲取處理模式描述
 */
function getProcessingMode(status: any): string {
    if (status.firebaseAvailable && status.macMiniStatus.available) {
        return '🚀 專業模式 (Firebase + Mac Mini)';
    } else if (status.firebaseAvailable) {
        return '☁️ 雲端模式 (Firebase + OpenRouter)';
    } else {
        return '📱 本地模式 (瀏覽器 + OpenRouter)';
    }
}

/**
 * 開始/停止錄音
 */
async function toggleRecording() {
    const status = enhancedRecorder.getStatus();
    
    if (status.isRecording) {
        await stopRecording();
    } else {
        await startRecording();
    }
}

/**
 * 開始錄音
 */
async function startRecording() {
    // 清理之前的結果
    currentResult = null;
    hideShareSection();
    clearResult();
    
    const success = await enhancedRecorder.startRecording();
    
    if (success) {
        updateRecordingUI(true);
        showStatus('錄音開始，正在進行語音識別...', 'success');
    } else {
        showStatus('錄音啟動失敗', 'error');
    }
}

/**
 * 停止錄音
 */
async function stopRecording() {
    const audioBlob = await enhancedRecorder.stopRecording();
    
    updateRecordingUI(false);
    
    if (audioBlob) {
        // 創建音頻預覽
        const audioUrl = URL.createObjectURL(audioBlob);
        const audioPlayer = document.getElementById('audioPlayer') as HTMLAudioElement;
        if (audioPlayer) {
            audioPlayer.src = audioUrl;
            audioPlayer.style.display = 'block';
        }
        
        const status = enhancedRecorder.getStatus();
        if (status.hasTranscript) {
            showStatus('錄音完成，可以開始 AI 分析', 'success');
        } else {
            showStatus('錄音完成，但未檢測到語音內容', 'warning');
        }
    } else {
        showStatus('錄音失敗', 'error');
    }
}

/**
 * 分析轉錄內容
 */
async function analyzeTranscript() {
    if (isProcessing) {
        showToast('分析進行中，請稍候...', 'warning');
        return;
    }
    
    const status = enhancedRecorder.getStatus();
    if (!status.hasTranscript) {
        showToast('請先錄音或上傳音頻文件', 'error');
        return;
    }
    
    const analysisTypeElement = document.getElementById('analysisType') as HTMLSelectElement;
    const analyzeBtn = document.getElementById('analyzeBtn') as HTMLButtonElement;
    
    if (!analysisTypeElement || !analyzeBtn) {
        showStatus('UI 元素未找到', 'error');
        return;
    }
    
    const selectedAnalysisType = analysisTypeElement.value;
    
    // 更新 UI 狀態
    isProcessing = true;
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = '🤖 AI 分析中...';
    
    hideShareSection();
    showResult('<div class="loading">⏳ AI 分析中，請稍候...</div>');
    
    try {
        // 獲取最後錄音的音頻
        const audioPlayer = document.getElementById('audioPlayer') as HTMLAudioElement;
        let audioBlob: Blob | null = null;
        
        if (audioPlayer && audioPlayer.src) {
            // 嘗試重新獲取音頻 Blob
            try {
                const response = await fetch(audioPlayer.src);
                audioBlob = await response.blob();
            } catch (e) {
                console.warn('無法獲取音頻 Blob，使用轉錄模式');
            }
        }
        
        // 如果沒有音頻 Blob，創建一個空的
        if (!audioBlob) {
            audioBlob = new Blob([], { type: 'audio/webm' });
        }
        
        // 執行處理
        const result = await enhancedRecorder.processAudio(audioBlob, selectedAnalysisType);
        currentResult = result;
        
        if (result.status === 'completed') {
            // 顯示轉錄結果
            if (result.transcript) {
                displayTranscriptSegments(result.transcript);
            }
            
            // 顯示分析結果
            if (result.analysis) {
                showResult(result.analysis);
                showShareSection();
                showStatus('AI 分析完成！', 'success');
            } else {
                showResult('分析完成，但未返回有效結果', true);
                showStatus('分析部分失敗', 'warning');
            }
            
            // 顯示說話者信息
            if (result.speakers && result.speakers.length > 0) {
                displaySpeakerInfo(result.speakers);
            }
            
        } else {
            const errorMsg = result.error || '分析失敗';
            showResult(`分析失敗：${errorMsg}`, true);
            showStatus(`分析失敗：${errorMsg}`, 'error');
        }
        
    } catch (error) {
        console.error('分析過程錯誤:', error);
        const errorMsg = error instanceof Error ? error.message : '未知錯誤';
        showResult(`分析失敗：${errorMsg}`, true);
        showStatus('分析失敗', 'error');
        
    } finally {
        // 恢復 UI 狀態
        isProcessing = false;
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = '🤖 開始AI分析';
    }
}

/**
 * 顯示轉錄分段
 */
function displayTranscriptSegments(segments: any[]) {
    const transcriptElement = document.getElementById('transcript');
    if (transcriptElement) {
        if (segments && segments.length > 0) {
            const formattedText = segments.map(seg => {
                const timeStr = seg.timestamp ? 
                    new Date(seg.timestamp).toLocaleTimeString() : 
                    `${Math.floor(seg.start || 0 / 60)}:${Math.floor(seg.start || 0 % 60).toString().padStart(2, '0')}`;
                const speakerStr = seg.speaker || 'SPEAKER';
                return `[${timeStr}] ${speakerStr}: ${seg.text}`;
            }).join('\\n');
            
            transcriptElement.textContent = formattedText;
        } else {
            transcriptElement.textContent = '無轉錄內容返回。';
        }
        
        // 自動滾動到底部
        transcriptElement.scrollTop = transcriptElement.scrollHeight;
    }
}

/**
 * 顯示說話者信息
 */
function displaySpeakerInfo(speakers: any[]) {
    const speakerInfoElement = document.getElementById('speakerInfo');
    if (speakerInfoElement) {
        // 計算說話者統計
        const speakerStats = new Map();
        
        speakers.forEach(seg => {
            const speaker = seg.speaker || 'UNKNOWN';
            const duration = (seg.end || 0) - (seg.start || 0);
            
            if (speakerStats.has(speaker)) {
                speakerStats.set(speaker, speakerStats.get(speaker) + duration);
            } else {
                speakerStats.set(speaker, duration);
            }
        });
        
        // 生成說話者信息 HTML
        const totalTime = Array.from(speakerStats.values()).reduce((a, b) => a + b, 0);
        const speakerHTML = Array.from(speakerStats.entries()).map(([speaker, time]) => {
            const percentage = totalTime > 0 ? ((time / totalTime) * 100).toFixed(1) : '0';
            const timeStr = `${Math.floor(time / 60)}:${Math.floor(time % 60).toString().padStart(2, '0')}`;
            
            return `
                <div class="speaker-stat">
                    <div class="speaker-name">${speaker.replace('SPEAKER_', 'Speaker ')}</div>
                    <div class="speaker-time">${timeStr} (${percentage}%)</div>
                    <div class="speaker-bar">
                        <div class="speaker-bar-fill" style="width: ${percentage}%"></div>
                    </div>
                </div>
            `;
        }).join('');
        
        speakerInfoElement.innerHTML = `
            <h3>說話者分析</h3>
            <div class="speaker-stats">
                ${speakerHTML}
            </div>
        `;
        speakerInfoElement.style.display = 'block';
    }
}

/**
 * 文件上傳處理
 */
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
            transcript.textContent = '音頻文件已上傳，點擊下方按鈕進行AI分析';
        }
        
        showStatus('音頻文件已上傳', 'success');
        
        // 清理之前的結果
        currentResult = null;
        hideShareSection();
    }
}

/**
 * 更新錄音 UI
 */
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
    
    // 重新檢查服務狀態
    setTimeout(() => checkServiceStatus(), 1000);
}

/**
 * 分享到 Line
 */
function shareToLine() {
    if (!currentResult || !currentResult.analysis) {
        showToast('沒有可分享的分析結果', 'error');
        return;
    }
    
    try {
        const analysisTypeElement = document.getElementById('analysisType') as HTMLSelectElement;
        const analysisTypeText = analysisTypeElement.options[analysisTypeElement.selectedIndex].text;
        
        const shareContent = formatShareContent(currentResult.analysis, analysisTypeText);
        
        // 使用 Web Share API 或 Line URL scheme
        if (navigator.share && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
            navigator.share({
                title: `AI會議分析 - ${analysisTypeText}`,
                text: shareContent
            }).then(() => {
                showToast('分享成功！', 'success');
            }).catch((error) => {
                if (error.name !== 'AbortError') {
                    fallbackToLineUrl(shareContent);
                }
            });
        } else {
            fallbackToLineUrl(shareContent);
        }
        
    } catch (error) {
        console.error('分享失敗:', error);
        showToast('分享失敗，請稍後再試', 'error');
    }
}

/**
 * Line URL scheme 分享
 */
function fallbackToLineUrl(shareContent: string) {
    try {
        const encodedText = encodeURIComponent(shareContent);
        const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
        
        const lineUrl = isMobile ? 
            `https://line.me/R/share?text=${encodedText}` :
            `https://social-plugins.line.me/lineit/share?text=${encodedText}`;
        
        window.open(lineUrl, '_blank');
        showToast('正在打開Line分享...', 'success');
        
    } catch (error) {
        console.error('Line 分享失敗:', error);
        showToast('分享失敗，請手動複製內容', 'error');
    }
}

/**
 * 複製結果
 */
function copyResult() {
    if (!currentResult || !currentResult.analysis) {
        showToast('沒有可複製的分析結果', 'error');
        return;
    }
    
    try {
        const analysisTypeElement = document.getElementById('analysisType') as HTMLSelectElement;
        const analysisTypeText = analysisTypeElement.options[analysisTypeElement.selectedIndex].text;
        
        const copyContent = formatCopyContent(currentResult.analysis, analysisTypeText);
        
        navigator.clipboard.writeText(copyContent).then(() => {
            showToast('已複製到剪貼板！', 'success');
        }).catch(() => {
            fallbackCopyText(copyContent);
        });
        
    } catch (error) {
        console.error('複製失敗:', error);
        showToast('複製失敗，請手動選取文字', 'error');
    }
}

/**
 * 備用複製方法
 */
function fallbackCopyText(text: string) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showToast('已複製到剪貼板！', 'success');
    } catch (error) {
        showToast('複製失敗，請手動選取文字', 'error');
    }
    
    document.body.removeChild(textArea);
}

/**
 * 格式化分享內容
 */
function formatShareContent(result: string, analysisType: string): string {
    const currentTime = new Date().toLocaleString('zh-TW');
    
    let content = result;
    if (content.length > 800) {
        content = content.substring(0, 800) + '...\\n\\n📄 完整內容請查看原始分析結果';
    }
    
    return `🤖 AI會議分析結果 - ${analysisType}\\n\\n${content}\\n\\n📅 分析時間：${currentTime}\\n🔗 使用工具：AI 會議助手 v2.0`;
}

/**
 * 格式化複製內容
 */
function formatCopyContent(result: string, analysisType: string): string {
    const currentTime = new Date().toLocaleString('zh-TW');
    
    return `🤖 AI會議分析結果 - ${analysisType}\\n\\n${result}\\n\\n📅 分析時間：${currentTime}\\n🔗 使用工具：AI 會議助手 v2.0`;
}

/**
 * 顯示/隱藏分享區域
 */
function showShareSection() {
    const shareSection = document.getElementById('shareSection');
    if (shareSection) {
        shareSection.classList.add('show');
    }
}

function hideShareSection() {
    const shareSection = document.getElementById('shareSection');
    if (shareSection) {
        shareSection.classList.remove('show');
    }
}

/**
 * 顯示提示訊息
 */
function showToast(message: string, type: 'success' | 'error' | 'warning' = 'success') {
    const toast = document.getElementById('toast');
    if (toast) {
        toast.textContent = message;
        toast.style.background = type === 'success' ? '#27ae60' : 
                                 type === 'error' ? '#e74c3c' : '#f39c12';
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
}

/**
 * 顯示狀態
 */
function showStatus(message: string, type: 'success' | 'error' | 'info' | 'warning' = 'info') {
    const status = document.getElementById('status');
    if (status) {
        status.textContent = message;
        status.className = `status ${type}`;
    }
}

/**
 * 顯示結果
 */
function showResult(content: string, isError: boolean = false) {
    const result = document.getElementById('result');
    if (result) {
        result.innerHTML = isError ? 
            `<div class="error">${content}</div>` : 
            `<div>${content.replace(/\\n/g, '<br>')}</div>`;
        result.style.display = 'block';
    }
}

/**
 * 清理結果
 */
function clearResult() {
    const result = document.getElementById('result');
    if (result) {
        result.innerHTML = '';
        result.style.display = 'none';
    }
    
    const transcript = document.getElementById('transcript');
    if (transcript) {
        transcript.textContent = '';
    }
    
    const speakerInfo = document.getElementById('speakerInfo');
    if (speakerInfo) {
        speakerInfo.style.display = 'none';
    }
}

/**
 * 重新檢查服務
 */
async function recheckServices() {
    showStatus('正在檢查服務狀態...', 'info');
    await checkServiceStatus();
    showToast('服務狀態已更新', 'success');
}

// 綁定全域函數
(window as any).toggleRecording = toggleRecording;
(window as any).stopRecording = stopRecording;
(window as any).handleFileUpload = handleFileUpload;
(window as any).analyzeTranscript = analyzeTranscript;
(window as any).shareToLine = shareToLine;
(window as any).copyResult = copyResult;
(window as any).recheckServices = recheckServices;

// 當 DOM 載入完成時初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// 清理資源
window.addEventListener('beforeunload', () => {
    enhancedRecorder.cleanup();
});
