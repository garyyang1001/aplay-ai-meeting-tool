"""
AI Meeting Tool Backend - 修復版本
修復問題：確保 job status API 能返回完整的處理結果
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

from pathlib import Path # Added for file size
# 自定義處理器
from processors.whisperx_processor import WhisperXProcessor
from processors.openrouter_client import OpenRouterClient
from utils.file_handler import FileHandler

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
cors_origins_str = os.getenv("CORS_ORIGINS")
allowed_origins = []
if cors_origins_str:
    allowed_origins = [origin.strip() for origin in cors_origins_str.split(',')]
    logger.info(f"CORS allowed origins configured from env: {allowed_origins}")
else:
    # Default behavior if CORS_ORIGINS is not set
    allowed_origins = ["*"]
    logger.warning("CORS_ORIGINS environment variable not set. Defaulting to allow all origins ('*'). "
                     "For production, it is highly recommended to set specific origins.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins, # Use the dynamically configured list
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全域變數
processor: Optional[WhisperXProcessor] = None
openrouter: Optional[OpenRouterClient] = None
file_handler_instance: Optional[FileHandler] = None # For FileHandler
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
    if not file_handler_instance:
        raise HTTPException(status_code=503, detail="FileHandler service is not initialized.")

    job_id = str(uuid.uuid4())
    saved_file_path = None # Initialize here to ensure it's available for finally block if sync

    try:
        # 初始化任務狀態 (early, before file saving, to track job_id)
        start_time = datetime.now()
        processing_jobs[job_id] = {
            "status": "processing",
            "step": "uploading",
            "progress": 1, # Initial progress
            "start_time": start_time,
            "original_filename": file.filename, # Store original filename
            "language": language,
            "analysis_type": analysis_type
        }

        logger.info(f"開始處理音訊 (Job: {job_id}): {file.filename}")

        # Save file using FileHandler
        try:
            saved_file_path = await file_handler_instance.save_uploaded_file(file, job_id)
            file_size = Path(saved_file_path).stat().st_size
            processing_jobs[job_id].update({
                "saved_file_path": saved_file_path,
                "file_size": file_size,
                "step": "preparing",
                "progress": 5
            })
            logger.info(f"檔案已儲存: {saved_file_path} (Job: {job_id}), 大小: {file_size} bytes")

        except ValueError as ve: # Catch validation errors from FileHandler
            logger.error(f"檔案驗證錯誤 (Job {job_id}): {ve}")
            processing_jobs[job_id].update({"status": "failed", "error": str(ve), "progress": 0})
            raise HTTPException(status_code=400, detail=str(ve))
        except RuntimeError as re: # Catch storage errors from FileHandler
            logger.error(f"檔案儲存錯誤 (Job {job_id}): {re}")
            processing_jobs[job_id].update({"status": "failed", "error": str(re), "progress": 0})
            raise HTTPException(status_code=500, detail=str(re))
        except Exception as e: # Catch any other unexpected error during file save
            logger.error(f"儲存檔案時發生未知錯誤 (Job {job_id}): {e}")
            processing_jobs[job_id].update({"status": "failed", "error": f"儲存檔案時發生未知錯誤: {e}", "progress": 0})
            raise HTTPException(status_code=500, detail=f"儲存檔案時發生未知錯誤: {e}")

        if async_processing:
            # 背景處理
            background_tasks.add_task(
                process_audio_background,
                job_id, saved_file_path, language, analysis_type,
                num_speakers, min_speakers, max_speakers
            )
            return ProcessingResponse(job_id=job_id, status="processing")
        else:
            # 同步處理
            result = await process_audio_sync(
                job_id, saved_file_path, language, analysis_type,
                num_speakers, min_speakers, max_speakers
            )
            return result
            
    except HTTPException as http_exc:
        # Log if not already properly logged by specific file handling errors
        if "error" not in processing_jobs.get(job_id, {}):
             processing_jobs[job_id] = {**processing_jobs.get(job_id, {}), "status": "failed", "error": http_exc.detail}
        raise
    except Exception as e:
        logger.error(f"處理音訊時發生主流程錯誤 (Job {job_id}): {e}")
        processing_jobs[job_id] = {**processing_jobs.get(job_id, {}), "status": "failed", "error": str(e), "progress": 0}
        raise HTTPException(status_code=500, detail=f"處理失敗: {str(e)}")
    finally:
        # Synchronous cleanup for synchronous calls.
        # For async, process_audio_sync (called by background task) handles its own cleanup.
        if not async_processing and saved_file_path and file_handler_instance:
            logger.info(f"同步處理完成，開始清理檔案 (Job {job_id}): {saved_file_path}")
            file_handler_instance.cleanup_temp_file(saved_file_path)


async def process_audio_sync(
    job_id: str, 
    audio_file_path: str,
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
        
        logger.info(f"開始 WhisperX 轉錄 (Job: {job_id})")
        
        # WhisperX 處理
        transcript_result = await processor.process_audio_file(
            audio_file_path=audio_file_path, # Pass path
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
        
        # 🔧 關鍵修復：儲存完整處理結果到 processing_jobs
        processing_jobs[job_id].update({
            "status": "completed",
            "step": "finished",
            "progress": 100,
            "processing_time": processing_time,
            # 新增：儲存實際處理結果
            "transcript": transcript_result["segments"],
            "speaker_count": transcript_result.get("diarization", {}).get("speaker_count", 0),
            "analysis": analysis,
            "detected_language": transcript_result["metadata"]["detected_language"],
            "diarization": transcript_result.get("diarization")
        })
        
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
        processing_jobs[job_id].update({
            "status": "failed",
            "error": str(e),
            "progress": 0 # Reset progress on failure
        })
        logger.error(f"同步音訊處理失敗 (Job {job_id}): {e}")
        raise # Re-raise to be caught by the main endpoint or background task handler
    finally:
        # Cleanup is handled by the caller of process_audio_sync if it's a direct sync call,
        # or here if it's part of a background task.
        # For this structure, if called by background task, it cleans up.
        # If called by sync route, the route's finally block cleans up.
        # To ensure cleanup for background tasks specifically:
        if asyncio.get_event_loop().is_running() and any(task.get_name() == job_id for task in asyncio.all_tasks()): # Heuristic for background
             if file_handler_instance and audio_file_path:
                logger.info(f"背景任務完成/失敗，開始清理檔案 (Job {job_id}): {audio_file_path}")
                file_handler_instance.cleanup_temp_file(audio_file_path)


async def process_audio_background(
    job_id: str, 
    audio_file_path: str,
    language: str, 
    analysis_type: str,
    num_speakers: Optional[int] = None,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None
):
    """背景處理音訊"""
    try:
        await process_audio_sync(
            job_id, audio_file_path, language, analysis_type,
            num_speakers, min_speakers, max_speakers
        )
    except Exception as e:
        logger.error(f"背景處理失敗 (Job {job_id}): {e}")
        # Ensure job status is updated if process_audio_sync failed to do so
        if job_id in processing_jobs and processing_jobs[job_id].get("status") != "failed":
            processing_jobs[job_id].update({
                "status": "failed",
                "error": f"背景任務執行失敗: {str(e)}",
                "progress": 0
            })
    finally:
        # Ensure cleanup for background tasks, even if process_audio_sync's finally didn't run due to early error
        # This is a fallback, ideally process_audio_sync's finally should always execute.
        # However, if process_audio_sync itself fails to enter its try block, this is needed.
        if file_handler_instance and audio_file_path:
            # Check if file still exists, as process_audio_sync might have cleaned it
            if Path(audio_file_path).exists():
                 logger.info(f"背景任務結束，確認清理檔案 (Job {job_id}): {audio_file_path}")
                 file_handler_instance.cleanup_temp_file(audio_file_path)


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
    """查詢任務狀態 - 🔧 修復版本：返回完整處理結果"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="任務不存在")
    
    job_status = processing_jobs[job_id].copy()
    
    # 計算運行時間
    if "start_time" in job_status and job_status["status"] == "processing":
        elapsed_time = (datetime.now() - job_status["start_time"]).total_seconds()
        job_status["elapsed_time"] = elapsed_time
    
    # 移除不需要的內部資訊，但保留處理結果
    job_status.pop("start_time", None)
    
    # 🔧 修復：確保返回完整結果給前端
    if job_status["status"] == "completed":
        # 確保包含所有前端需要的欄位
        return {
            "job_id": job_id,
            "status": job_status["status"],
            "step": job_status.get("step", "finished"),
            "progress": job_status.get("progress", 100),
            "original_filename": job_status.get("original_filename"),
            "language": job_status.get("detected_language", job_status.get("language")),
            "analysis_type": job_status.get("analysis_type"),
            "saved_file_path": job_status.get("saved_file_path"),
            "file_size": job_status.get("file_size"),
            "processing_time": job_status.get("processing_time"),
            # 🎯 關鍵：返回實際處理結果
            "transcript": job_status.get("transcript"),
            "speaker_count": job_status.get("speaker_count"),
            "analysis": job_status.get("analysis"),
            "diarization": job_status.get("diarization")
        }
    
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
    global processor, openrouter, file_handler_instance
    
    logger.info("🚀 AI Meeting Tool Backend 啟動中...")
    
    # 初始化 FileHandler
    try:
        file_handler_instance = FileHandler()
        logger.info(f"✅ FileHandler initialized. Upload dir: {file_handler_instance.upload_dir}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize FileHandler: {e}")
        file_handler_instance = None # Ensure it's defined for checks; server might proceed or halt based on policy
        # Depending on policy, might raise an error here to stop server startup
        # raise RuntimeError(f"Critical component FileHandler failed to initialize: {e}") from e

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
        
        # Read BATCH_SIZE from environment variables
        batch_size_env = os.getenv("BATCH_SIZE", "16")
        batch_size = int(batch_size_env) if batch_size_env.isdigit() else 16

        # Read COMPUTE_TYPE from environment variables
        compute_type = os.getenv("COMPUTE_TYPE", "float16")
        # Optional: Add validation for allowed compute types
        allowed_compute_types = ["float16", "float32", "int8"]
        if compute_type not in allowed_compute_types:
            logger.warning(f"無效的 COMPUTE_TYPE: {compute_type}. 使用預設值 'float16'.")
            compute_type = "float16"

        processor = WhisperXProcessor(
            model_size=model_size,
            device=device,
            language=language,
            compute_type=compute_type, # Pass the value from env
            batch_size=batch_size    # Pass the value from env
        )
        logger.info(f"✅ WhisperX 處理器初始化完成 (模型: {model_size}, 設備: {device}, 語言: {language}, 計算類型: {compute_type}, 批次大小: {batch_size})")
        
        # 初始化 OpenRouter 客戶端
        logger.info("🤖 初始化 OpenRouter 客戶端...")
        openrouter = OpenRouterClient()
        logger.info("✅ OpenRouter 客戶端初始化完成")
        
        # 建立臨時目錄 (FileHandler now manages its own directories)
        # temp_dir = os.getenv("TEMP_DIR", "/tmp/ai_meeting_tool") # No longer needed here if FileHandler manages
        # os.makedirs(temp_dir, exist_ok=True)
        # logger.info(f"📁 臨時目錄已建立: {temp_dir}") # Commented out
        
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
