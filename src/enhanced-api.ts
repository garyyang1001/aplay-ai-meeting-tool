/**
 * 增強版 API 客戶端
 * 整合瀏覽器語音識別 + 後端 WhisperX + OpenRouter 分析
 */

export interface TranscriptSegment {
    start: number;
    end: number;
    text: string;
    speaker: string;
    words?: Array<{
        start: number;
        end: number;
        word: string;
        score: number;
    }>;
}

export interface ProcessingResponse {
    job_id: string;
    status: string;
    transcript?: TranscriptSegment[];
    speaker_count?: number;
    analysis?: string;
    processing_time?: number;
    language?: string;
    analysis_type?: string;
    diarization?: {
        speaker_count: number;
        speakers: string[];
        speaker_times: Record<string, number>;
        speaker_percentages: Record<string, number>;
    };
    error?: string;
}

export interface JobStatus {
    status: string;
    step?: string;
    progress?: number;
    elapsed_time?: number;
    error?: string;
}

export class EnhancedAPIClient {
    private backendUrl: string;
    private openRouterKey: string;
    
    constructor(backendUrl?: string, openRouterKey?: string) {
        this.backendUrl = backendUrl || this.detectBackendUrl();
        this.openRouterKey = openRouterKey || this.getOpenRouterKey();
    }
    
    private detectBackendUrl(): string {
        // 自動偵測後端 URL
        const hostname = window.location.hostname;
        
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return 'http://localhost:8000';
        } else {
            // 生產環境，假設後端在相同域名的 8000 port
            return `${window.location.protocol}//${hostname}:8000`;
        }
    }
    
    private getOpenRouterKey(): string {
        // 從環境變數或 localStorage 獲取 API Key
        return (import.meta as any).env?.VITE_OPENROUTER_API_KEY || 
               localStorage.getItem('openrouter_api_key') || '';
    }
    
    /**
     * 雙軌策略：優先使用後端 WhisperX，降級到瀏覽器 + OpenRouter
     */
    async processAudio(
        audioBlob: Blob, 
        options: {
            language?: string;
            analysisType?: string;
            numSpeakers?: number;
            asyncProcessing?: boolean;
            useBackend?: boolean;
        } = {}
    ): Promise<ProcessingResponse> {
        
        const {
            language = 'zh',
            analysisType = '會議摘要',
            numSpeakers,
            asyncProcessing = false,
            useBackend = true
        } = options;
        
        try {
            if (useBackend) {
                // 路徑 1：使用後端 WhisperX + OpenRouter
                return await this.processWithBackend(audioBlob, {
                    language,
                    analysisType,
                    numSpeakers,
                    asyncProcessing
                });
            } else {
                throw new Error('Backend disabled, using browser fallback');
            }
        } catch (backendError) {
            console.warn('後端處理失敗，降級到瀏覽器處理:', backendError);
            
            // 路徑 2：降級到瀏覽器語音識別 + OpenRouter
            return await this.processWithBrowser(audioBlob, {
                language,
                analysisType
            });
        }
    }
    
    /**
     * 後端 WhisperX 處理（主要路徑）
     */
    private async processWithBackend(
        audioBlob: Blob,
        options: {
            language: string;
            analysisType: string;
            numSpeakers?: number;
            asyncProcessing: boolean;
        }
    ): Promise<ProcessingResponse> {
        
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.webm');
        formData.append('language', options.language);
        formData.append('analysis_type', options.analysisType);
        formData.append('async_processing', options.asyncProcessing.toString());
        
        if (options.numSpeakers) {
            formData.append('num_speakers', options.numSpeakers.toString());
        }
        
        const response = await fetch(`${this.backendUrl}/process-audio`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`後端處理失敗 (${response.status}): ${errorText}`);
        }
        
        const result: ProcessingResponse = await response.json();
        
        // 如果是異步處理，輪詢狀態
        if (options.asyncProcessing && result.status === 'processing') {
            return await this.waitForJobCompletion(result.job_id);
        }
        
        return result;
    }
    
    /**
     * 瀏覽器處理（降級路徑）
     */
    private async processWithBrowser(
        audioBlob: Blob,
        options: {
            language: string;
            analysisType: string;
        }
    ): Promise<ProcessingResponse> {
        
        try {
            // 使用瀏覽器語音識別
            const transcript = await this.transcribeWithBrowser(audioBlob, options.language);
            
            // 使用 OpenRouter 分析
            let analysis = '';
            if (this.openRouterKey) {
                analysis = await this.analyzeWithOpenRouter(transcript, options.analysisType);
            } else {
                analysis = '無法進行 AI 分析：缺少 OpenRouter API Key';
            }
            
            return {
                job_id: 'browser_' + Date.now(),
                status: 'completed',
                transcript: transcript,
                speaker_count: new Set(transcript.map(t => t.speaker)).size,
                analysis: analysis,
                processing_time: 0,
                language: options.language,
                analysis_type: options.analysisType
            };
            
        } catch (error) {
            throw new Error(`瀏覽器處理失敗: ${error instanceof Error ? error.message : '未知錯誤'}`);
        }
    }
    
    /**
     * 瀏覽器語音識別
     */
    private async transcribeWithBrowser(audioBlob: Blob, language: string): Promise<TranscriptSegment[]> {
        return new Promise((resolve, reject) => {
            const SpeechRecognition = (window as any).SpeechRecognition || 
                                    (window as any).webkitSpeechRecognition;
            
            if (!SpeechRecognition) {
                reject(new Error('瀏覽器不支援語音識別'));
                return;
            }
            
            const recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = false;
            recognition.lang = language === 'zh' ? 'zh-TW' : 'en-US';
            
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            
            const segments: TranscriptSegment[] = [];
            let currentSpeaker = 'SPEAKER_00';
            
            recognition.onresult = (event: any) => {
                for (let i = 0; i < event.results.length; i++) {
                    if (event.results[i].isFinal) {
                        const transcript = event.results[i][0].transcript;
                        segments.push({
                            start: i * 3, // 估算時間
                            end: (i + 1) * 3,
                            text: transcript.trim(),
                            speaker: currentSpeaker
                        });
                        
                        // 簡單的說話者切換邏輯
                        if (Math.random() > 0.7) {
                            currentSpeaker = currentSpeaker === 'SPEAKER_00' ? 'SPEAKER_01' : 'SPEAKER_00';
                        }
                    }
                }
            };
            
            recognition.onerror = (event: any) => {
                reject(new Error(`語音識別錯誤: ${event.error}`));
            };
            
            recognition.onend = () => {
                URL.revokeObjectURL(audioUrl);
                resolve(segments);
            };
            
            // 播放音訊並開始識別
            audio.play();
            recognition.start();
            
            // 音訊結束後停止識別
            audio.onended = () => {
                recognition.stop();
            };
        });
    }
    
    /**
     * OpenRouter 分析
     */
    private async analyzeWithOpenRouter(transcript: TranscriptSegment[], analysisType: string): Promise<string> {
        if (!this.openRouterKey) {
            throw new Error('缺少 OpenRouter API Key');
        }
        
        const formattedTranscript = transcript
            .map(seg => `[${seg.start.toFixed(1)}s] ${seg.speaker}: ${seg.text}`)
            .join('\n');
        
        const prompt = this.getAnalysisPrompt(analysisType);
        const fullPrompt = `${prompt}\n\n會議錄音轉錄內容：\n${formattedTranscript}`;
        
        const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.openRouterKey}`,
                'HTTP-Referer': window.location.origin,
                'X-Title': 'AI Meeting Tool',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: 'google/gemma-3-27b-it:free',
                messages: [
                    {
                        role: 'system',
                        content: 'You are a professional meeting analysis assistant. Please respond in Traditional Chinese.'
                    },
                    {
                        role: 'user',
                        content: fullPrompt
                    }
                ],
                temperature: 0.7,
                max_tokens: 3000
            })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`OpenRouter API 錯誤 (${response.status}): ${errorText}`);
        }
        
        const data = await response.json();
        return data.choices[0]?.message?.content || '分析失敗';
    }
    
    /**
     * 等待異步任務完成
     */
    private async waitForJobCompletion(jobId: string, maxWaitTime: number = 300000): Promise<ProcessingResponse> {
        const startTime = Date.now();
        
        while (Date.now() - startTime < maxWaitTime) {
            try {
                const status = await this.getJobStatus(jobId);
                
                if (status.status === 'completed') {
                    // 獲取最終結果（這裡假設後端會在任務完成後提供完整結果）
                    return {
                        job_id: jobId,
                        status: 'completed',
                        ...status
                    } as ProcessingResponse;
                } else if (status.status === 'failed') {
                    throw new Error(status.error || '處理失敗');
                }
                
                // 等待 2 秒後再次檢查
                await new Promise(resolve => setTimeout(resolve, 2000));
                
            } catch (error) {
                console.error('檢查任務狀態失敗:', error);
                await new Promise(resolve => setTimeout(resolve, 5000));
            }
        }
        
        throw new Error('任務處理超時');
    }
    
    /**
     * 獲取任務狀態
     */
    async getJobStatus(jobId: string): Promise<JobStatus> {
        const response = await fetch(`${this.backendUrl}/job/${jobId}/status`);
        
        if (!response.ok) {
            throw new Error(`無法獲取任務狀態: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    /**
     * 分析已有轉錄文字
     */
    async analyzeTranscript(transcript: TranscriptSegment[], analysisType: string): Promise<string> {
        try {
            // 優先使用後端
            const response = await fetch(`${this.backendUrl}/analyze-transcript`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    transcript: transcript,
                    analysis_type: analysisType
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                return data.analysis;
            }
        } catch (error) {
            console.warn('後端分析失敗，使用前端分析:', error);
        }
        
        // 降級到前端 OpenRouter
        return await this.analyzeWithOpenRouter(transcript, analysisType);
    }
    
    /**
     * 健康檢查
     */
    async healthCheck(): Promise<{ backend: boolean; openrouter: boolean }> {
        const result = { backend: false, openrouter: false };
        
        // 檢查後端
        try {
            const response = await fetch(`${this.backendUrl}/health`, { 
                method: 'GET',
                timeout: 5000 as any 
            });
            result.backend = response.ok;
        } catch {
            result.backend = false;
        }
        
        // 檢查 OpenRouter
        result.openrouter = !!this.openRouterKey;
        
        return result;
    }
    
    /**
     * 獲取系統資訊
     */
    async getSystemInfo(): Promise<any> {
        try {
            const response = await fetch(`${this.backendUrl}/models/info`);
            if (response.ok) {
                return await response.json();
            }
        } catch {
            // 後端不可用時的降級資訊
        }
        
        return {
            backend_available: false,
            browser_features: {
                speech_recognition: !!(window as any).SpeechRecognition || !!(window as any).webkitSpeechRecognition,
                media_recorder: !!window.MediaRecorder,
                audio_context: !!(window as any).AudioContext || !!(window as any).webkitAudioContext
            }
        };
    }
    
    private getAnalysisPrompt(analysisType: string): string {
        const prompts: Record<string, string> = {
            '會議摘要': '請為以下會議內容提供詳細摘要，包含主要議題、討論重點、達成共識和未解決問題。',
            '行動項目': '請從以下會議內容中提取具體的行動項目，包含任務內容、負責人員、截止時間和優先順序。',
            '重要決策': '請列出以下會議中的所有重要決策，包含決策內容、理由、影響和執行方式。',
            '智能分析': '請對以下會議進行深度分析，包含效率評估、參與度分析、改善建議和目標達成度評估。'
        };
        
        return prompts[analysisType] || prompts['會議摘要'];
    }
}

// 導出單例實例
export const apiClient = new EnhancedAPIClient();
