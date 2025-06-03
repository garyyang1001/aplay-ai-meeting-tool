export interface ChatMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
}

export interface OpenRouterResponse {
    choices: {
        message: {
            content: string;
        };
    }[];
}

export class OpenRouterAPI {
    private apiKey: string;
    private baseUrl = 'https://openrouter.ai/api/v1/chat/completions';
    private model = 'google/gemma-3-27b-it:free';
    
    constructor(apiKey: string) {
        this.apiKey = apiKey;
    }
    
    async chat(userMessage: string): Promise<string> {
        const messages: ChatMessage[] = [
            {
                role: 'system',
                content: 'You are a professional meeting analysis assistant. Please respond in Traditional Chinese. Your task is to help users analyze meeting content and provide clear, structured analysis results.'
            },
            {
                role: 'user',
                content: userMessage
            }
        ];
        
        try {
            const response = await fetch(this.baseUrl, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.apiKey}`,
                    'HTTP-Referer': window.location.origin,
                    'X-Title': 'AI Meeting Tool',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    model: this.model,
                    messages: messages,
                    temperature: 0.7,
                    max_tokens: 2000
                })
            });
            
            if (!response.ok) {
                const errorData = await response.text();
                throw new Error(`API request failed (${response.status}): ${errorData}`);
            }
            
            const data: OpenRouterResponse = await response.json();
            
            if (!data.choices || data.choices.length === 0) {
                throw new Error('API returned invalid response');
            }
            
            return data.choices[0].message.content.trim();
            
        } catch (error) {
            console.error('OpenRouter API error:', error);
            
            if (error instanceof TypeError && error.message.includes('fetch')) {
                throw new Error('網路連接錯誤，請檢查網路連接');
            }
            
            throw error;
        }
    }
    
    // 測試 API 連接
    async testConnection(): Promise<boolean> {
        try {
            await this.chat('測試連接');
            return true;
        } catch (error) {
            console.error('API connection test failed:', error);
            return false;
        }
    }
}