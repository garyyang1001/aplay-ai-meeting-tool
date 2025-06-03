"""
OpenRouter API 客戶端
支援 google/gemma-3-27b-it:free 模型進行會議分析
"""

import requests
import json
import os
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class OpenRouterClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key is required")
        
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "google/gemma-3-27b-it:free"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://aplay-ai-meeting-tool.vercel.app",
            "X-Title": "AI Meeting Tool",
            "Content-Type": "application/json"
        }
    
    async def analyze_transcript(self, transcript_segments: List[Dict], analysis_type: str) -> str:
        """
        分析會議轉錄內容
        
        Args:
            transcript_segments: 轉錄片段列表 [{"text": "...", "speaker": "...", "start": 0.0, "end": 1.0}]
            analysis_type: 分析類型 ("會議摘要", "行動項目", "重要決策", "智能分析")
        
        Returns:
            分析結果文字
        """
        try:
            # 格式化轉錄內容
            formatted_transcript = self._format_transcript(transcript_segments)
            
            # 獲取分析提示詞
            prompt = self._get_analysis_prompt(analysis_type)
            
            # 構建完整提示
            full_prompt = f"{prompt}\n\n會議錄音轉錄內容：\n{formatted_transcript}"
            
            # 檢查內容長度
            if len(full_prompt) > 100000:  # 約 80K tokens
                logger.warning(f"Content too long ({len(full_prompt)} chars), truncating...")
                truncated_transcript = self._truncate_content(formatted_transcript, 80000)
                full_prompt = f"{prompt}\n\n會議錄音轉錄內容（已截取前80000字）：\n{truncated_transcript}"
            
            # 調用 API
            response = await self._call_api(full_prompt)
            return response
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            raise Exception(f"AI 分析失敗：{str(e)}")
    
    def _format_transcript(self, segments: List[Dict]) -> str:
        """格式化轉錄片段為可讀文字"""
        if not segments:
            return "無轉錄內容"
        
        formatted_lines = []
        for segment in segments:
            speaker = segment.get("speaker", "UNKNOWN")
            text = segment.get("text", "").strip()
            start_time = segment.get("start", 0)
            
            if text:
                # 格式化時間戳（分:秒）
                minutes = int(start_time // 60)
                seconds = int(start_time % 60)
                timestamp = f"{minutes:02d}:{seconds:02d}"
                
                formatted_lines.append(f"[{timestamp}] {speaker}: {text}")
        
        return "\n".join(formatted_lines)
    
    def _get_analysis_prompt(self, analysis_type: str) -> str:
        """獲取分析類型對應的提示詞"""
        prompts = {
            "會議摘要": """請為以下會議內容提供詳細摘要，包含：
1. 主要議題和討論重點
2. 關鍵觀點和論述
3. 達成的共識或結論
4. 未解決的問題
請用繁體中文回答，保持客觀和結構化。""",

            "行動項目": """請從以下會議內容中提取具體的行動項目，包含：
1. 具體要執行的任務
2. 負責人員（如果有提到）
3. 截止時間或時程
4. 優先順序評估
請用繁體中文回答，以清單格式呈現。""",

            "重要決策": """請列出以下會議中的所有重要決策，包含：
1. 決策的具體內容
2. 決策的理由和背景
3. 預期的影響和後果
4. 執行方式和時程
請用繁體中文回答，按重要性排序。""",

            "智能分析": """請對以下會議進行深度分析，包含：
1. 會議效率和品質評估
2. 參與者貢獻度分析
3. 討論模式和互動特徵
4. 潛在問題和改善建議
5. 會議目標達成度評估
請用繁體中文回答，提供客觀且具建設性的分析。"""
        }
        
        return prompts.get(analysis_type, prompts["會議摘要"])
    
    def _truncate_content(self, content: str, max_length: int) -> str:
        """智能截取內容，避免截斷重要資訊"""
        if len(content) <= max_length:
            return content
        
        # 在句號或換行處截取
        truncated = content[:max_length]
        last_period = max(truncated.rfind('。'), truncated.rfind('\n'))
        
        if last_period > max_length * 0.8:
            return truncated[:last_period + 1]
        
        return truncated
    
    async def _call_api(self, prompt: str) -> str:
        """調用 OpenRouter API"""
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional meeting analysis assistant. Please respond in Traditional Chinese. Provide clear, structured, and actionable analysis results."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 4000,
            "top_p": 0.9
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                error_detail = response.text[:500]
                raise Exception(f"API 請求失敗 ({response.status_code}): {error_detail}")
            
            data = response.json()
            
            if "choices" not in data or not data["choices"]:
                raise Exception("API 回應格式錯誤：無 choices 欄位")
            
            result = data["choices"][0]["message"]["content"].strip()
            
            if not result:
                raise Exception("API 回應為空")
            
            return result
            
        except requests.exceptions.Timeout:
            raise Exception("API 請求超時，請稍後重試")
        except requests.exceptions.ConnectionError:
            raise Exception("網路連接錯誤，請檢查網路連接")
        except json.JSONDecodeError:
            raise Exception("API 回應格式錯誤")
        except Exception as e:
            if "API" in str(e):
                raise e
            else:
                raise Exception(f"未知錯誤：{str(e)}")
    
    async def test_connection(self) -> bool:
        """測試 API 連接"""
        try:
            await self._call_api("這是一個連接測試，請簡短回應。")
            return True
        except Exception as e:
            logger.error(f"API connection test failed: {str(e)}")
            return False
    
    def get_supported_analysis_types(self) -> List[str]:
        """獲取支援的分析類型"""
        return ["會議摘要", "行動項目", "重要決策", "智能分析"]
