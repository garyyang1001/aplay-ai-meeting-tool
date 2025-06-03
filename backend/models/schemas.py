from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class TranscriptSegment(BaseModel):
    """
    轉錄片段模型
    """
    start: float = Field(..., description="開始時間（秒）")
    end: float = Field(..., description="結束時間（秒）")
    text: str = Field(..., description="轉錄文字")
    speaker: Optional[str] = Field(None, description="說話者標識")
    confidence: Optional[float] = Field(None, description="信心分數 (0-1)")
    words: Optional[List[Dict[str, Any]]] = Field(None, description="詞級詳細資訊")

class WordSegment(BaseModel):
    """
    詞級片段模型
    """
    word: str = Field(..., description="單詞")
    start: float = Field(..., description="開始時間（秒）")
    end: float = Field(..., description="結束時間（秒）")
    confidence: Optional[float] = Field(None, description="信心分數")
    speaker: Optional[str] = Field(None, description="說話者標識")

class ProcessingRequest(BaseModel):
    """
    處理請求模型
    """
    language: str = Field(default="zh", description="語言代碼")
    analysis_type: str = Field(default="會議摘要", description="分析類型")
    num_speakers: Optional[int] = Field(None, description="說話者數量")
    min_speakers: Optional[int] = Field(None, description="最少說話者數量")
    max_speakers: Optional[int] = Field(None, description="最多說話者數量")
    custom_prompt: Optional[str] = Field(None, description="自訂分析提示")

class ProcessingResponse(BaseModel):
    """
    處理回應模型
    """
    job_id: str = Field(..., description="任務 ID")
    status: str = Field(..., description="處理狀態")
    transcript: List[TranscriptSegment] = Field(..., description="轉錄結果")
    word_segments: Optional[List[WordSegment]] = Field(None, description="詞級片段")
    speaker_count: int = Field(..., description="說話者數量")
    analysis: str = Field(..., description="AI 分析結果")
    processing_time: float = Field(..., description="處理時間（秒）")
    language: str = Field(..., description="檢測到的語言")
    analysis_type: str = Field(..., description="分析類型")
    metadata: Optional[Dict[str, Any]] = Field(None, description="額外元數據")

class JobStatus(BaseModel):
    """
    任務狀態模型
    """
    job_id: str = Field(..., description="任務 ID")
    status: str = Field(..., description="狀態：processing, completed, failed")
    progress: int = Field(default=0, description="進度百分比 (0-100)")
    step: Optional[str] = Field(None, description="當前步驟")
    error: Optional[str] = Field(None, description="錯誤訊息")
    start_time: Optional[datetime] = Field(None, description="開始時間")
    estimated_completion: Optional[datetime] = Field(None, description="預估完成時間")

class AnalysisRequest(BaseModel):
    """
    分析請求模型
    """
    transcript: List[TranscriptSegment] = Field(..., description="轉錄內容")
    analysis_type: str = Field(default="會議摘要", description="分析類型")
    custom_prompt: Optional[str] = Field(None, description="自訂提示")

class AnalysisResponse(BaseModel):
    """
    分析回應模型
    """
    status: str = Field(..., description="分析狀態")
    analysis: str = Field(..., description="分析結果")
    analysis_type: str = Field(..., description="分析類型")
    processing_time: Optional[float] = Field(None, description="處理時間")

class SystemStats(BaseModel):
    """
    系統統計模型
    """
    system: Dict[str, Any] = Field(..., description="系統資源使用情況")
    jobs: Dict[str, Any] = Field(..., description="任務統計")
    models: Dict[str, Any] = Field(default_factory=dict, description="模型狀態")
    timestamp: datetime = Field(default_factory=datetime.now, description="統計時間")

class HealthCheck(BaseModel):
    """
    健康檢查模型
    """
    status: str = Field(..., description="服務狀態")
    timestamp: datetime = Field(..., description="檢查時間")
    components: Dict[str, Any] = Field(..., description="各組件狀態")
    version: Optional[str] = Field(None, description="服務版本")

class ErrorResponse(BaseModel):
    """
    錯誤回應模型
    """
    error: str = Field(..., description="錯誤類型")
    message: str = Field(..., description="錯誤訊息")
    detail: Optional[str] = Field(None, description="詳細錯誤資訊")
    timestamp: datetime = Field(default_factory=datetime.now, description="錯誤時間")
    job_id: Optional[str] = Field(None, description="相關任務 ID")

class ModelInfo(BaseModel):
    """
    模型資訊模型
    """
    name: str = Field(..., description="模型名稱")
    type: str = Field(..., description="模型類型")
    description: str = Field(..., description="模型描述")
    languages: List[str] = Field(..., description="支援語言")
    capabilities: List[str] = Field(..., description="支援功能")
    status: str = Field(..., description="模型狀態")

class ConfigSettings(BaseModel):
    """
    配置設定模型
    """
    whisper_model: str = Field(default="large-v2", description="Whisper 模型大小")
    batch_size: int = Field(default=16, description="批次大小")
    compute_type: str = Field(default="float16", description="計算精度")
    device: str = Field(default="auto", description="計算設備")
    max_file_size: int = Field(default=100, description="最大檔案大小（MB）")
    supported_languages: List[str] = Field(default=["zh", "en", "ja", "ko"], description="支援語言")
    default_language: str = Field(default="zh", description="預設語言")
    max_concurrent_jobs: int = Field(default=3, description="最大並發任務數")