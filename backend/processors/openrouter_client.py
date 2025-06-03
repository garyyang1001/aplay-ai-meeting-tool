import os
import httpx
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class OpenRouterClient:
    """
    OpenRouter API 客戶端
    用於 AI 智能分析功能
    """
    
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.base_url = 'https://openrouter.ai/api/v1/chat/completions'
        self.model = 'google/gemma-3-27b-it:free'
        self.timeout = 60.0
        
        if not self.api_key:
            logger.warning("未設定 OPENROUTER_API_KEY，AI 分析功能將無法使用")
        
        logger.info(f"OpenRouter 客戶端初始化，模型: {self.model}")
    
    def health_check(self) -> str:
        """健康檢查"""
        if not self.api_key:
            return "api_key_missing"
        return "ready"
    
    async def analyze_transcript(
        self, 
        segments: List[Dict], 
        analysis_type: str = "會議摘要"
    ) -> str:
        """
        分析轉錄內容
        
        Args:
            segments: 轉錄片段列表
            analysis_type: 分析類型
        
        Returns:
            分析結果文字
        """
        if not self.api_key:
            raise RuntimeError("OpenRouter API 金鑰未設定")
        
        try:
            # 格式化轉錄內容
            formatted_transcript = self._format_transcript(segments)
            
            # 取得分析提示
            prompt = self._get_analysis_prompt(analysis_type)
            
            logger.info(f"開始 AI 分析，類型: {analysis_type}")
            
            # 發送 API 請求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'HTTP-Referer': 'https://ai-meeting-tool.com',
                        'X-Title': 'AI Meeting Tool',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': self.model,
                        'messages': [{
                            'role': 'user',
                            'content': f"{prompt}\n\n會議記錄：\n{formatted_transcript}"
                        }],
                        'temperature': 0.7,
                        'max_tokens': 2000
                    }
                )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result['choices'][0]['message']['content']
                
                logger.info(f"AI 分析完成，長度: {len(analysis)} 字元")
                return analysis
            else:
                error_msg = f"OpenRouter API 錯誤: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
        
        except httpx.TimeoutException:
            logger.error("OpenRouter API 請求超時")
            raise RuntimeError("AI 分析請求超時，請稍後重試")
        
        except Exception as e:
            logger.error(f"AI 分析時發生錯誤: {e}")
            raise RuntimeError(f"AI 分析失敗: {str(e)}")
    
    def _format_transcript(self, segments: List[Dict]) -> str:
        """
        格式化轉錄內容
        
        Args:
            segments: 轉錄片段
        
        Returns:
            格式化的文字
        """
        formatted_lines = []
        
        for segment in segments:
            # 取得時間戳記
            start_time = segment.get('start', 0)
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            
            # 取得說話者
            speaker = segment.get('speaker', 'UNKNOWN')
            if speaker.startswith('SPEAKER_'):
                speaker_name = f"說話者{speaker.split('_')[1]}"
            else:
                speaker_name = speaker
            
            # 取得文字內容
            text = segment.get('text', '').strip()
            
            if text:
                formatted_lines.append(f"{timestamp} {speaker_name}: {text}")
        
        return '\n'.join(formatted_lines)
    
    def _get_analysis_prompt(self, analysis_type: str) -> str:
        """
        取得分析提示詞
        
        Args:
            analysis_type: 分析類型
        
        Returns:
            提示詞
        """
        prompts = {
            '會議摘要': """
請為以下會議記錄提供詳細摘要，包含：

1. **會議主題與目的**
2. **主要討論重點** (按重要性排序)
3. **達成的共識與決定**
4. **未解決的問題或爭議**
5. **會議效果評估**

請用繁體中文回答，條理清晰，重點突出。
            """,
            
            '行動項目': """
請從會議記錄中提取所有行動項目，包含：

1. **具體任務描述**
2. **負責人員** (如果會議中有提到)
3. **完成期限** (如果會議中有討論)
4. **優先級評估** (高/中/低)
5. **相關資源需求**

請以表格或清單形式呈現，用繁體中文回答。
            """,
            
            '重要決策': """
請列出會議中的所有重要決策，包含：

1. **決策內容** (具體描述)
2. **決策依據** (討論過程和理由)
3. **預期影響** (對團隊、專案、業務的影響)
4. **執行方式** (如何落實這個決策)
5. **風險評估** (可能的挑戰或問題)

請用繁體中文回答，重點突出決策的重要性和影響。
            """,
            
            '智能分析': """
請提供會議的全面智能分析，包含：

1. **會議效率評估** (時間運用、議程執行)
2. **參與者貢獻度分析** (發言頻率、質量評估)
3. **討論深度分析** (話題探討的深度和廣度)
4. **溝通效果評估** (理解程度、共識達成)
5. **改善建議** (提升未來會議效果的具體建議)
6. **關鍵洞察** (會議中的重要發現或趨勢)

請用繁體中文回答，提供深入的分析和實用的建議。
            """,
            
            '情感分析': """
請分析會議中的情感氛圍和溝通狀態：

1. **整體氛圍** (積極、中性、消極)
2. **參與者情緒狀態** (投入度、滿意度)
3. **溝通風格分析** (合作型、競爭型、迴避型)
4. **潛在衝突或分歧**
5. **團隊凝聚力評估**
6. **建議** (改善團隊溝通的方法)

請用繁體中文回答，客觀分析但避免過度解讀。
            """,
            
            '關鍵字提取': """
請從會議記錄中提取：

1. **核心關鍵字** (最重要的 10-15 個關鍵詞)
2. **專業術語** (領域相關的專門用語)
3. **人名和組織** (會議中提到的重要人物或機構)
4. **時間節點** (重要的日期或時程安排)
5. **數字資訊** (重要的數據、指標、金額等)

請用繁體中文整理，按類別分組呈現。
            """
        }
        
        return prompts.get(analysis_type, prompts['會議摘要'])
    
    async def custom_analysis(
        self, 
        segments: List[Dict], 
        custom_prompt: str
    ) -> str:
        """
        自訂分析提示
        
        Args:
            segments: 轉錄片段
            custom_prompt: 自訂提示詞
        
        Returns:
            分析結果
        """
        if not self.api_key:
            raise RuntimeError("OpenRouter API 金鑰未設定")
        
        try:
            formatted_transcript = self._format_transcript(segments)
            
            logger.info("開始自訂 AI 分析")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'HTTP-Referer': 'https://ai-meeting-tool.com',
                        'X-Title': 'AI Meeting Tool',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': self.model,
                        'messages': [{
                            'role': 'user',
                            'content': f"{custom_prompt}\n\n會議記錄：\n{formatted_transcript}"
                        }],
                        'temperature': 0.7,
                        'max_tokens': 2000
                    }
                )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result['choices'][0]['message']['content']
                logger.info("自訂 AI 分析完成")
                return analysis
            else:
                error_msg = f"OpenRouter API 錯誤: {response.status_code}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
        
        except Exception as e:
            logger.error(f"自訂 AI 分析時發生錯誤: {e}")
            raise RuntimeError(f"自訂分析失敗: {str(e)}")
    
    def get_available_analysis_types(self) -> List[Dict[str, str]]:
        """
        取得可用的分析類型
        
        Returns:
            分析類型列表
        """
        return [
            {
                "type": "會議摘要",
                "description": "整體會議概述，包含主要議題、討論重點和達成共識",
                "icon": "📝"
            },
            {
                "type": "行動項目",
                "description": "提取具體的待辦事項、負責人和時程安排",
                "icon": "✅"
            },
            {
                "type": "重要決策",
                "description": "識別會議中的重要決策，包含依據、影響和執行方式",
                "icon": "🎯"
            },
            {
                "type": "智能分析",
                "description": "深度分析會議效率、參與度和溝通效果",
                "icon": "🤖"
            },
            {
                "type": "情感分析",
                "description": "分析會議氛圍、參與者情緒和團隊動態",
                "icon": "😊"
            },
            {
                "type": "關鍵字提取",
                "description": "提取重要關鍵字、專業術語和核心資訊",
                "icon": "🔍"
            }
        ]
    
    def get_model_info(self) -> Dict[str, str]:
        """
        取得模型資訊
        
        Returns:
            模型資訊
        """
        return {
            "model": self.model,
            "provider": "Google",
            "description": "Gemma-3 27B 指令調校版本，專為對話和分析任務優化",
            "cost": "免費",
            "context_length": "8192 tokens",
            "languages": "支援多種語言，包含繁體中文"
        }