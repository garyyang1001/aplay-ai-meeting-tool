"""
AI Meeting Tool Backend - FastAPI 主程式
整合 WhisperX 轉錄和 OpenRouter AI 分析
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import tempfile
import uuid
import asyncio
from datetime import datetime
import logging
import json

# 自定義處理器
from processors.whisperx_processor import WhisperXProcessor
from processors.openrouter_client import OpenRouterClient

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic 模型
class AnalyzeTranscriptRequest(BaseModel):
    transcript: List[Dict[str, Any]]
    analysis_type: str = "會議摘要"

class ProcessingResponse(BaseModel):
    job_id: str
    status: str
    transcript: Optional[List[Dict[str, Any]]] = None
    speaker_count: Optional[int] = None
    analysis: Optional[str] = None
    processing_time: Optional[float] = None
    language: Optional[str] = None
    analysis_type: Optional[str] = None
    diarization: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# 建立 FastAPI 應用
app = FastAPI(
    title="AI Meeting Tool Backend",
    description="基於 WhisperX 和 OpenRouter 的會議錄音轉錄和智能分析 API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 設置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境應限制特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全域變數
processor: Optional[WhisperXProcessor] = None
openrouter: Optional[OpenRouterClient] = None
processing_jobs = {}

@app.get("/")
async def root():
    """根端點 - 系統狀態"""
    return {
        "message": "🤖 AI Meeting Tool Backend",
        "version": "2.0.0",
        "status": "running",
        "features": [
            "WhisperX 語音轉錄",
            "精準說話者辨識", 
            "OpenRouter AI 分析",
            "即時處理狀態"
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        # 檢查 WhisperX 處理器
        if processor:
            whisperx_info = processor.get_model_info()
            health_status["components"]["whisperx"] = {
                "status": "ready",
                **whisperx_info
            }
        else:
            health_status["components"]["whisperx"] = {"status": "not_initialized"}
        
        # 檢查 OpenRouter 客戶端
        if openrouter:
            try:
                # 簡單的連接測試
                connection_ok = await openrouter.test_connection()
                health_status["components"]["openrouter"] = {
                    "status": "ready" if connection_ok else "connection_failed"
                }
            except Exception as e:
                health_status["components"]["openrouter"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            health_status["components"]["openrouter"] = {"status": "not_initialized"}
        
        return health_status
        
    except Exception as e:
        logger.error(f"健康檢查失敗: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.post("/process-audio", response_model=ProcessingResponse)
async def process_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form("zh"),
    analysis_type: str = Form("會議摘要"),
    num_speakers: Optional[int] = Form(None),
    min_speakers: Optional[int] = Form(None),
    max_speakers: Optional[int] = Form(None),
    async_processing: bool = Form(False)
):
    """
    處理上傳的音訊檔案
    
    - **file**: 音訊檔案 (支援 MP3, WAV, M4A, WEBM, OGG, FLAC)
    - **language**: 語言代碼 (zh=中文, en=英文, auto=自動偵測)
    - **analysis_type**: 分析類型 (會議摘要, 行動項目, 重要決策, 智能分析)
    - **num_speakers**: 精確說話者數量
    - **min_speakers**: 最少說話者數量
    - **max_speakers**: 最多說話者數量
    - **async_processing**: 是否背景處理
    """
    
    if not processor or not openrouter:
        raise HTTPException(status_code=503, detail="服務尚未初始化完成")
    
    job_id = str(uuid.uuid4())
    
    try:
        # 驗證檔案
        if not file.filename:
            raise HTTPException(status_code=400, detail="檔案名稱不能為空")
        
        # 檢查檔案格式
        allowed_extensions = {'.mp3', '.wav', '.m4a', '.webm', '.ogg', '.flac', '.opus'}
        file_ext = os.path.splitext(file.filename.lower())[1]
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"不支援的檔案格式 {file_ext}。支援格式：{', '.join(allowed_extensions)}"
            )
        
        # 讀取檔案內容
        file_content = await file.read()
        file_size = len(file_content)
        
        # 檢查檔案大小 (預設 100MB)
        max_size = int(os.getenv("MAX_FILE_SIZE", "100")) * 1024 * 1024
        if file_size > max_size:
            raise HTTPException(
                status_code=413, 
                detail=f"檔案大小 {file_size//1024//1024}MB 超過限制 {max_size//1024//1024}MB"
            )
        
        # 初始化任務狀態
        start_time = datetime.now()
        processing_jobs[job_id] = {
            "status": "processing",
            "step": "preparing",
            "progress": 5,
            "start_time": start_time,
            "filename": file.filename,
            "file_size": file_size,
            "language": language,
            "analysis_type": analysis_type
        }
        
        logger.info(f"開始處理音訊: {file.filename} ({file_size} bytes), Job: {job_id}")
        
        if async_processing:
            # 背景處理
            background_tasks.add_task(
                process_audio_background,
                job_id, file_content, file.filename, language, analysis_type,
                num_speakers, min_speakers, max_speakers
            )
            
            return ProcessingResponse(
                job_id=job_id,
                status="processing"
            )
        else:
            # 同步處理
            result = await process_audio_sync(
                job_id, file_content, file.filename, language, analysis_type,
                num_speakers, min_speakers, max_speakers
            )
            return result
            
    except HTTPException:
        # 重新拋出 HTTP 異常
        processing_jobs[job_id] = {
            "status": "failed",
            "error": "檔案驗證失敗"
        }
        raise
    except Exception as e:
        logger.error(f"處理音訊時發生錯誤: {e}")
        processing_jobs[job_id] = {
            "status": "failed",
            "error": str(e),
            "progress": 0
        }
        raise HTTPException(status_code=500, detail=f"處理失敗: {str(e)}")

async def process_audio_sync(
    job_id: str, 
    file_content: bytes, 
    filename: str, 
    language: str, 
    analysis_type: str,
    num_speakers: Optional[int] = None,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None
) -> ProcessingResponse:
    """同步處理音訊"""
    
    try:
        # 更新狀態：開始轉錄
        processing_jobs[job_id]["step"] = "transcribing"
        processing_jobs[job_id]["progress"] = 20
        
        logger.info(f"開始 WhisperX 轉錄: {job_id}")
        
        # WhisperX 處理
        transcript_result = await processor.process_audio_file(
            file_content=file_content,
            filename=filename,
            language=language,
            num_speakers=num_speakers,
            min_speakers=min_speakers,
            max_speakers=max_speakers
        )
        
        # 更新狀態：開始 AI 分析
        processing_jobs[job_id]["step"] = "analyzing"
        processing_jobs[job_id]["progress"] = 75
        
        logger.info(f"開始 AI 分析: {job_id}")
        
        # OpenRouter 分析
        analysis = await openrouter.analyze_transcript(
            transcript_result["segments"], 
            analysis_type
        )
        
        # 計算處理時間
        processing_time = (datetime.now() - processing_jobs[job_id]["start_time"]).total_seconds()
        
        # 完成處理
        processing_jobs[job_id] = {
            **processing_jobs[job_id],
            "status": "completed",
            "step": "finished",
            "progress": 100,
            "processing_time": processing_time
        }
        
        logger.info(f"處理完成: {job_id}, 耗時: {processing_time:.2f}秒")
        
        # 返回結果
        return ProcessingResponse(
            job_id=job_id,
            status="completed",
            transcript=transcript_result["segments"],
            speaker_count=transcript_result.get("diarization", {}).get("speaker_count", 0),
            analysis=analysis,
            processing_time=processing_time,
            language=transcript_result["metadata"]["detected_language"],
            analysis_type=analysis_type,
            diarization=transcript_result.get("diarization")
        )
        
    except Exception as e:
        # 處理失敗
        processing_jobs[job_id] = {
            **processing_jobs[job_id],
            "status": "failed",
            "error": str(e),
            "progress": 0
        }
        raise

async def process_audio_background(
    job_id: str, 
    file_content: bytes, 
    filename: str, 
    language: str, 
    analysis_type: str,
    num_speakers: Optional[int] = None,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None
):
    """背景處理音訊"""
    try:
        await process_audio_sync(
            job_id, file_content, filename, language, analysis_type,
            num_speakers, min_speakers, max_speakers
        )
    except Exception as e:
        logger.error(f"背景處理失敗 {job_id}: {e}")

@app.post("/analyze-transcript")
async def analyze_transcript(request: AnalyzeTranscriptRequest):
    """分析已有的轉錄文字"""
    
    if not openrouter:
        raise HTTPException(status_code=503, detail="OpenRouter 服務尚未初始化")
    
    try:
        analysis = await openrouter.analyze_transcript(
            request.transcript, 
            request.analysis_type
        )
        
        return {
            "status": "completed",
            "analysis": analysis,
            "analysis_type": request.analysis_type,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"分析轉錄文字時發生錯誤: {e}")
        raise HTTPException(status_code=500, detail=f"分析失敗: {str(e)}")

@app.get("/job/{job_id}/status")
async def get_job_status(job_id: str):
    """查詢任務狀態"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="任務不存在")
    
    job_status = processing_jobs[job_id].copy()
    
    # 計算運行時間
    if "start_time" in job_status and job_status["status"] == "processing":
        elapsed_time = (datetime.now() - job_status["start_time"]).total_seconds()
        job_status["elapsed_time"] = elapsed_time
    
    # 移除不需要的內部資訊
    job_status.pop("start_time", None)
    
    return job_status

@app.get("/models/info")
async def get_model_info():
    """獲取模型資訊"""
    info = {
        "whisperx": None,
        "openrouter": None,
        "supported_features": []
    }
    
    if processor:
        info["whisperx"] = processor.get_model_info()
        info["supported_features"].append("語音轉錄")
        if info["whisperx"]["models_loaded"]["diarization"]:
            info["supported_features"].append("說話者辨識")
    
    if openrouter:
        info["openrouter"] = {
            "model": "google/gemma-3-27b-it:free",
            "supported_analysis_types": openrouter.get_supported_analysis_types()
        }
        info["supported_features"].append("AI 智能分析")
    
    info["supported_languages"] = [
        {"code": "zh", "name": "中文"},
        {"code": "en", "name": "English"},
        {"code": "ja", "name": "日本語"},
        {"code": "ko", "name": "한국어"},
        {"code": "auto", "name": "自動偵測"}
    ]
    
    info["supported_formats"] = [
        "MP3", "WAV", "M4A", "WEBM", "OGG", "FLAC", "OPUS"
    ]
    
    return info

@app.get("/stats")
async def get_stats():
    """系統統計資訊"""
    try:
        # 任務統計
        total_jobs = len(processing_jobs)
        completed_jobs = sum(1 for job in processing_jobs.values() if job.get("status") == "completed")
        failed_jobs = sum(1 for job in processing_jobs.values() if job.get("status") == "failed")
        processing_count = sum(1 for job in processing_jobs.values() if job.get("status") == "processing")
        
        stats = {
            "jobs": {
                "total": total_jobs,
                "completed": completed_jobs,
                "failed": failed_jobs,
                "processing": processing_count,
                "success_rate": round((completed_jobs / total_jobs * 100), 2) if total_jobs > 0 else 0
            },
            "system": {
                "uptime": "運行中",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # 嘗試獲取系統資源資訊
        try:
            import psutil
            stats["system"].update({
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent
            })
        except ImportError:
            logger.info("psutil not available, skipping system resource stats")
        
        # GPU 資訊
        if processor:
            model_info = processor.get_model_info()
            stats["gpu"] = {
                "cuda_available": model_info["cuda_available"],
                "device": model_info["device"]
            }
        
        return stats
        
    except Exception as e:
        logger.error(f"獲取統計資訊失敗: {e}")
        return {"error": f"無法獲取統計資訊: {str(e)}"}

@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """刪除任務記錄"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="任務不存在")
    
    job_status = processing_jobs[job_id]["status"]
    if job_status == "processing":
        raise HTTPException(status_code=400, detail="無法刪除進行中的任務")
    
    del processing_jobs[job_id]
    return {"message": f"任務 {job_id} 已刪除"}

@app.delete("/jobs")
async def clear_completed_jobs():
    """清理已完成的任務"""
    completed_jobs = [
        job_id for job_id, job in processing_jobs.items() 
        if job["status"] in ["completed", "failed"]
    ]
    
    for job_id in completed_jobs:
        del processing_jobs[job_id]
    
    return {"message": f"已清理 {len(completed_jobs)} 個已完成的任務"}

@app.on_event("startup")
async def startup_event():
    """應用啟動初始化"""
    global processor, openrouter
    
    logger.info("🚀 AI Meeting Tool Backend 啟動中...")
    
    # 檢查必要的環境變數
    required_env_vars = ["HF_TOKEN", "OPENROUTER_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ 缺少必要的環境變數: {missing_vars}")
        logger.info("請設置以下環境變數：")
        logger.info("HF_TOKEN - HuggingFace API Token (用於說話者辨識)")
        logger.info("OPENROUTER_API_KEY - OpenRouter API Key (用於 AI 分析)")
        raise RuntimeError(f"請設置環境變數: {missing_vars}")
    
    try:
        # 初始化 WhisperX 處理器
        logger.info("📝 初始化 WhisperX 處理器...")
        model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
        device = os.getenv("DEVICE", "auto")
        language = os.getenv("DEFAULT_LANGUAGE", "zh")
        
        processor = WhisperXProcessor(
            model_size=model_size,
            device=device,
            language=language
        )
        logger.info(f"✅ WhisperX 處理器初始化完成 (模型: {model_size}, 設備: {device})")
        
        # 初始化 OpenRouter 客戶端
        logger.info("🤖 初始化 OpenRouter 客戶端...")
        openrouter = OpenRouterClient()
        logger.info("✅ OpenRouter 客戶端初始化完成")
        
        # 建立臨時目錄
        temp_dir = os.getenv("TEMP_DIR", "/tmp/ai_meeting_tool")
        os.makedirs(temp_dir, exist_ok=True)
        logger.info(f"📁 臨時目錄已建立: {temp_dir}")
        
        logger.info("🎉 AI Meeting Tool Backend 啟動完成！")
        logger.info("📖 API 文檔：http://localhost:8000/docs")
        
    except Exception as e:
        logger.error(f"❌ 啟動失敗: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉清理"""
    logger.info("🛑 AI Meeting Tool Backend 正在關閉...")
    
    # 清理資源
    if processor:
        try:
            processor._cleanup_memory()
            logger.info("✅ WhisperX 資源已清理")
        except:
            pass
    
    logger.info("👋 AI Meeting Tool Backend 已關閉")

if __name__ == "__main__":
    import uvicorn
    
    # 從環境變數讀取配置
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
