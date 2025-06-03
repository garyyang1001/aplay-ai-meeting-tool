/**
 * 增強型錄音處理器
 * 整合 Firebase 上傳、Mac Mini 處理、OpenRouter 備用方案
 */

import firebaseService from './firebase-service';
import { apiClient } from './enhanced-api';

export interface TranscriptSegment {
    text: string;
    timestamp: number;
    speaker?: string;
    confidence?: number;
}

export interface ProcessingResult {
    status: 'completed' | 'failed' | 'processing';
    transcript?: TranscriptSegment[];
    analysis?: string;
    speakers?: any[];
    jobId?: string;
    error?: string;
}

class EnhancedRecorder {
    private mediaRecorder: MediaRecorder | null = null;
    private audioStream: MediaStream | null = null;
    private recognition: any = null;
    private isRecording = false;
    private audioChunks: Blob[] = [];
    private transcript: TranscriptSegment[] = [];
    private recordingStartTime = 0;
    private recordingTimer: NodeJS.Timeout | null = null;
    private statusCallback: ((message: string, type?: string) => void) | null = null;

    constructor() {
        this.initializeSpeechRecognition();
        this.initializeFirebase();
    }

    /**
     * 設置狀態回調
     */
    setStatusCallback(callback: (message: string, type?: string) => void) {
        this.statusCallback = callback;
    }

    private showStatus(message: string, type: string = 'info') {
        console.log(`[${type.toUpperCase()}] ${message}`);
        if (this.statusCallback) {
            this.statusCallback(message, type);
        }
    }

    /**
     * 初始化 Firebase
     */
    private async initializeFirebase() {
        try {
            const initialized = await firebaseService.initialize();
            if (initialized) {
                this.showStatus('Firebase 服務已準備就緒', 'success');
            } else {
                this.showStatus('Firebase 服務不可用，將使用本地模式', 'warning');
            }
        } catch (error) {
            this.showStatus('Firebase 初始化失敗', 'error');
        }
    }

    /**
     * 初始化語音識別
     */
    private initializeSpeechRecognition() {
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        
        if (SpeechRecognition) {
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            this.recognition.lang = 'zh-TW';
            
            this.recognition.onresult = (event: any) => {
                this.handleSpeechResult(event);
            };
            
            this.recognition.onerror = (event: any) => {
                console.error('語音識別錯誤:', event.error);
                this.showStatus(`語音識別錯誤: ${event.error}`, 'error');
            };
            
            this.recognition.onend = () => {
                if (this.isRecording) {
                    // 重新啟動語音識別
                    setTimeout(() => {
                        if (this.recognition && this.isRecording) {
                            try {
                                this.recognition.start();
                            } catch (e) {
                                console.log('語音識別重啟失敗:', e);
                            }
                        }
                    }, 100);
                }
            };
        }
    }

    /**
     * 處理語音識別結果
     */
    private handleSpeechResult(event: any) {
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            
            if (result.isFinal) {
                const segment: TranscriptSegment = {
                    text: result[0].transcript,
                    timestamp: Date.now(),
                    confidence: result[0].confidence
                };
                
                this.transcript.push(segment);
                this.updateTranscriptDisplay();
            }
        }
    }

    /**
     * 更新轉錄顯示
     */
    private updateTranscriptDisplay() {
        const transcriptElement = document.getElementById('transcript');
        if (transcriptElement) {
            const displayText = this.transcript
                .map(seg => `[${new Date(seg.timestamp).toLocaleTimeString()}] ${seg.text}`)
                .join('\\n');
            transcriptElement.textContent = displayText;
            transcriptElement.scrollTop = transcriptElement.scrollHeight;
        }
    }

    /**
     * 開始錄音
     */
    async startRecording(): Promise<boolean> {
        if (this.isRecording) {
            return false;
        }

        try {
            // 重置狀態
            this.audioChunks = [];
            this.transcript = [];
            this.recordingStartTime = Date.now();

            // 請求麥克風權限
            this.audioStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 44100
                }
            });

            // 設置 MediaRecorder
            const options = { mimeType: 'audio/webm;codecs=opus' };
            try {
                this.mediaRecorder = new MediaRecorder(this.audioStream, options);
            } catch (e) {
                this.mediaRecorder = new MediaRecorder(this.audioStream);
            }

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            // 開始錄音
            this.mediaRecorder.start(1000);
            this.isRecording = true;

            // 開始語音識別
            if (this.recognition) {
                try {
                    this.recognition.start();
                } catch (e) {
                    this.showStatus('語音識別啟動失敗，僅進行錄音', 'warning');
                }
            }

            // 開始計時器
            this.startTimer();

            this.showStatus('錄音開始...', 'success');
            return true;

        } catch (error) {
            console.error('錄音啟動失敗:', error);
            this.showStatus('錄音啟動失敗，請檢查麥克風權限', 'error');
            return false;
        }
    }

    /**
     * 停止錄音
     */
    async stopRecording(): Promise<Blob | null> {
        if (!this.isRecording) {
            return null;
        }

        this.isRecording = false;

        // 停止錄音
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
        }

        // 停止語音識別
        if (this.recognition) {
            try {
                this.recognition.stop();
            } catch (e) {
                console.log('語音識別停止失敗:', e);
            }
        }

        // 停止音頻流
        if (this.audioStream) {
            this.audioStream.getTracks().forEach(track => track.stop());
            this.audioStream = null;
        }

        // 停止計時器
        this.stopTimer();

        // 創建音頻 Blob
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        
        this.showStatus('錄音完成', 'success');
        return audioBlob;
    }

    /**
     * 處理音頻檔案
     */
    async processAudio(
        audioBlob: Blob, 
        analysisType: string = '會議摘要'
    ): Promise<ProcessingResult> {
        
        const jobId = `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        this.showStatus('開始處理音頻...', 'info');

        try {
            // 1. 檢查 Mac Mini 狀態
            const macMiniStatus = await firebaseService.checkMacMiniStatus();
            
            if (macMiniStatus.available && firebaseService.isAvailable()) {
                // 路徑 A: Firebase + Mac Mini 處理
                return await this.processWithMacMini(audioBlob, jobId, analysisType);
            } else {
                // 路徑 B: 直接使用 OpenRouter 處理
                this.showStatus('Mac Mini 不可用，使用備用處理方案', 'warning');
                return await this.processWithOpenRouter(audioBlob, analysisType);
            }

        } catch (error) {
            console.error('音頻處理失敗:', error);
            return {
                status: 'failed',
                error: error instanceof Error ? error.message : '未知錯誤',
                jobId
            };
        }
    }

    /**
     * 使用 Mac Mini 處理
     */
    private async processWithMacMini(
        audioBlob: Blob, 
        jobId: string, 
        analysisType: string
    ): Promise<ProcessingResult> {
        
        try {
            this.showStatus('上傳音頻到 Firebase...', 'info');
            
            // 上傳音頻到 Firebase
            const audioUrl = await firebaseService.uploadAudio(audioBlob, jobId);
            if (!audioUrl) {
                throw new Error('音頻上傳失敗');
            }

            // 創建處理任務記錄
            const taskId = await firebaseService.createProcessingJob({
                id: jobId,
                audioUrl,
                transcript: this.transcript,
                status: 'pending'
            });

            if (!taskId) {
                throw new Error('任務創建失敗');
            }

            this.showStatus('發送處理請求到 Mac Mini...', 'info');
            
            // 發送處理請求到 Mac Mini
            const sent = await firebaseService.sendToMacMini(
                jobId, 
                audioUrl, 
                this.transcript
            );

            if (!sent) {
                throw new Error('發送到 Mac Mini 失敗');
            }

            this.showStatus('等待 Mac Mini 處理中...', 'info');

            // 輪詢結果
            const result = await firebaseService.pollForResult(jobId, 60);
            
            if (!result) {
                throw new Error('處理超時或失敗');
            }

            if (result.status === 'completed') {
                this.showStatus('Mac Mini 處理完成！', 'success');
                
                // 同時使用 OpenRouter 進行分析
                let analysis = result.analysis;
                if (!analysis && this.transcript.length > 0) {
                    this.showStatus('使用 OpenRouter 進行分析增強...', 'info');
                    const openRouterResult = await this.analyzeWithOpenRouter(
                        this.transcript, 
                        analysisType
                    );
                    analysis = openRouterResult;
                }

                return {
                    status: 'completed',
                    transcript: result.enhanced_transcript || this.transcript,
                    speakers: result.speakers,
                    analysis,
                    jobId
                };
            } else {
                throw new Error(result.error || '處理失敗');
            }

        } catch (error) {
            console.error('Mac Mini 處理失敗:', error);
            
            // 降級到 OpenRouter
            this.showStatus('降級到 OpenRouter 處理...', 'warning');
            return await this.processWithOpenRouter(audioBlob, analysisType);
        }
    }

    /**
     * 使用 OpenRouter 處理
     */
    private async processWithOpenRouter(
        audioBlob: Blob, 
        analysisType: string
    ): Promise<ProcessingResult> {
        
        try {
            this.showStatus('使用 OpenRouter 進行分析...', 'info');

            // 如果沒有轉錄，使用現有的轉錄
            let transcript = this.transcript;
            
            if (transcript.length === 0) {
                this.showStatus('無轉錄文字，請先錄音', 'error');
                return {
                    status: 'failed',
                    error: '無轉錄文字可供分析'
                };
            }

            // 使用 OpenRouter 分析
            const analysis = await this.analyzeWithOpenRouter(transcript, analysisType);

            this.showStatus('OpenRouter 分析完成！', 'success');

            return {
                status: 'completed',
                transcript,
                analysis,
                speakers: this.generateMockSpeakers(transcript) // 生成基本的說話者信息
            };

        } catch (error) {
            console.error('OpenRouter 處理失敗:', error);
            return {
                status: 'failed',
                error: error instanceof Error ? error.message : 'OpenRouter 處理失敗'
            };
        }
    }

    /**
     * 使用 OpenRouter 分析轉錄文字
     */
    private async analyzeWithOpenRouter(
        transcript: TranscriptSegment[], 
        analysisType: string
    ): Promise<string> {
        
        // 格式化轉錄文字
        const transcriptText = transcript
            .map((seg, index) => `[${new Date(seg.timestamp).toLocaleTimeString()}] ${seg.text}`)
            .join('\\n');

        // 使用現有的 API 客戶端
        const response = await apiClient.analyzeText(transcriptText, analysisType);
        
        if (response && response.analysis) {
            return response.analysis;
        } else {
            throw new Error('OpenRouter 分析失敗');
        }
    }

    /**
     * 生成模擬說話者信息
     */
    private generateMockSpeakers(transcript: TranscriptSegment[]): any[] {
        // 基於轉錄文字的簡單說話者分段
        // 實際實作可以根據停頓時間、音調變化等來判斷
        const speakers = [];
        let currentSpeaker = 'SPEAKER_00';
        let segmentCount = 0;
        
        for (const seg of transcript) {
            // 每 3 個片段換一個說話者（簡單模擬）
            if (segmentCount > 0 && segmentCount % 3 === 0) {
                currentSpeaker = currentSpeaker === 'SPEAKER_00' ? 'SPEAKER_01' : 'SPEAKER_00';
            }
            
            speakers.push({
                speaker: currentSpeaker,
                start: (seg.timestamp - this.recordingStartTime) / 1000,
                end: (seg.timestamp - this.recordingStartTime) / 1000 + 5, // 假設 5 秒
                text: seg.text
            });
            
            segmentCount++;
        }
        
        return speakers;
    }

    /**
     * 開始計時器
     */
    private startTimer() {
        this.recordingTimer = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.recordingStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            
            const recordingTime = document.getElementById('recordingTime');
            if (recordingTime) {
                recordingTime.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
        }, 1000);
    }

    /**
     * 停止計時器
     */
    private stopTimer() {
        if (this.recordingTimer) {
            clearInterval(this.recordingTimer);
            this.recordingTimer = null;
        }
        
        const recordingTime = document.getElementById('recordingTime');
        if (recordingTime) {
            recordingTime.textContent = '00:00';
        }
    }

    /**
     * 獲取當前狀態
     */
    getStatus() {
        return {
            isRecording: this.isRecording,
            hasTranscript: this.transcript.length > 0,
            transcriptLength: this.transcript.length,
            firebaseAvailable: firebaseService.isAvailable(),
            macMiniStatus: firebaseService.getMacMiniStatus()
        };
    }

    /**
     * 清理資源
     */
    cleanup() {
        this.stopRecording();
        firebaseService.cleanupLocalBackups();
    }
}

// 導出單例
export const enhancedRecorder = new EnhancedRecorder();
export default enhancedRecorder;
