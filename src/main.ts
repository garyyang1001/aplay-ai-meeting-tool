import { OpenRouterAPI } from './api';

// 全域變數
let api: OpenRouterAPI;

// 初始化
function init() {
    console.log('阿玩AI會議工具啟動中...');
    
    // 檢查環境變數
    const apiKey = (import.meta as any).env.VITE_OPENROUTER_API_KEY as string;
    if (!apiKey) {
        showStatus('警告：未設定 API Key', 'error');
        return;
    }
    
    api = new OpenRouterAPI(apiKey);
    showStatus('系統已就緒');
    
    // 設定事件監聽器
    setupEventListeners();
}

function setupEventListeners() {
    const analysisType = document.getElementById('analysisType') as HTMLSelectElement;
    const customPromptSection = document.getElementById('customPromptSection') as HTMLDivElement;
    
    analysisType.addEventListener('change', () => {
        if (analysisType.value === 'custom') {
            customPromptSection.style.display = 'block';
        } else {
            customPromptSection.style.display = 'none';
        }
    });
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
            `<div class="error">${content}</div>` : 
            `<div>${content.replace(/\n/g, '<br>')}</div>`;
        result.style.display = 'block';
    }
}

function getPromptTemplate(type: string, customPrompt?: string): string {
    const templates = {
        summary: '請為以下會議內容提供一個簡潔明確的摘要，包含主要討論點和結論：',
        action_items: '請從以下會議內容中提取出所有需要執行的行動項目，包含負責人和時間點：',
        key_decisions: '請列出以下會議內容中做出的所有重要決策和決定：',
        follow_up: '請分析以下會議內容，並建議需要後續追蹤的事項和時間點：',
        custom: customPrompt || '請分析以下內容：'
    };
    
    return templates[type as keyof typeof templates] || templates.summary;
}

// 全域函數供 HTML 調用
(window as any).analyzeContent = async function() {
    const contentElement = document.getElementById('meetingContent') as HTMLTextAreaElement;
    const analysisTypeElement = document.getElementById('analysisType') as HTMLSelectElement;
    const customPromptElement = document.getElementById('customPrompt') as HTMLInputElement;
    const analyzeBtn = document.getElementById('analyzeBtn') as HTMLButtonElement;
    
    const content = contentElement.value.trim();
    const analysisType = analysisTypeElement.value;
    const customPrompt = customPromptElement.value.trim();
    
    if (!content) {
        showResult('請輸入會議內容', true);
        return;
    }
    
    if (!api) {
        showResult('API 未初始化，請檢查設定', true);
        return;
    }
    
    // 顯示載入狀態
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = '🤔 AI思考中...';
    showStatus('正在分析中，請稍候...');
    showResult('<div class="loading">⏳ AI正在分析您的會議內容...</div>');
    
    try {
        const prompt = getPromptTemplate(analysisType, customPrompt);
        const fullPrompt = `${prompt}\n\n會議內容：\n${content}`;
        
        const response = await api.chat(fullPrompt);
        
        showResult(response);
        showStatus('分析完成！');
        
    } catch (error) {
        console.error('分析錯誤:', error);
        showResult(`分析失敗：${error instanceof Error ? error.message : '未知錯誤'}`, true);
        showStatus('分析失敗', 'error');
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = '🚀 開始分析';
    }
};

// 當 DOM 載入完成時初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}