from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import tempfile
import uuid
from datetime import datetime
import logging

# 自定義模組
from processors.whisperx_processor import WhisperXProcessor
from processors.openrouter_client import OpenRouterClient
from models.schemas import ProcessingRequest, ProcessingResponse
from utils.file_handler import FileHandler
from utils.firebase_client import FirebaseClient

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 建立 FastAPI 應用
app = FastAPI(
    title="AI Meeting Tool Backend",
    description="基於 WhisperX 的會議錄音轉錄和智能分析 API",
    version="2.0.0"
)

# CORS 設置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境應限制特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化處理器
processor = WhisperXProcessor()
openrouter = OpenRouterClient()
file_handler = FileHandler()
firebase_client = FirebaseClient()

# 處理中的任務儲存
processing_jobs = {}

@app.get("/")
async def root():
    return {
        "message": "AI Meeting Tool Backend",
        "version": "2.0.0",
        "status": "running",
        "whisperx_ready": processor.is_ready(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    try:
        # 檢查各個組件狀態
        whisperx_status = processor.health_check()
        openrouter_status = openrouter.health_check()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "whisperx": whisperx_status,
                "openrouter": openrouter_status,
                "file_handler": "ready"
            }
        }
    except Exception as e:
        logger.error(f"健康檢查失敗: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.post("/process-audio", response_model=ProcessingResponse)
async def process_audio(
    file: UploadFile = File(...),
    language: str = "zh",
    analysis_type: str = "會議摘要",
    num_speakers: int = None,
    background_tasks: BackgroundTasks = None
):
    """處理上傳的音訊檔案"""
    
    job_id = str(uuid.uuid4())
    
    try:
        # 驗證檔案
        if not file.filename:
            raise HTTPException(status_code=400, detail="檔案名稱不能為空")
        
        # 檢查檔案大小
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        max_size = int(os.getenv("MAX_FILE_SIZE", "100")) * 1024 * 1024  # 預設 100MB
        if file_size > max_size:
            raise HTTPException(
                status_code=413, 
                detail=f"檔案大小超過限制 ({max_size // 1024 // 1024}MB)"
            )
        
        # 重置檔案指針
        await file.seek(0)
        
        # 記錄開始時間
        start_time = datetime.now()
        
        logger.info(f"開始處理音訊檔案: {file.filename}, 大小: {file_size} bytes, 任務ID: {job_id}")
        
        # 保存上傳檔案
        audio_path = await file_handler.save_uploaded_file(file, job_id)
        
        # 更新任務狀態
        processing_jobs[job_id] = {
            "status": "processing",
            "step": "transcribing",
            "progress": 10,
            "start_time": start_time
        }
        
        # WhisperX 處理
        logger.info(f"開始 WhisperX 轉錄: {job_id}")
        transcript_result = processor.process_meeting_audio(
            audio_path, 
            language=language,
            num_speakers=num_speakers
        )
        
        # 更新進度
        processing_jobs[job_id]["step"] = "analyzing"
        processing_jobs[job_id]["progress"] = 70
        
        # OpenRouter 分析
        logger.info(f"開始 AI 分析: {job_id}")
        analysis = await openrouter.analyze_transcript(
            transcript_result["segments"], 
            analysis_type
        )
        
        # 計算處理時間
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 清理暫存檔案
        file_handler.cleanup_temp_file(audio_path)
        
        # 完成處理
        processing_jobs[job_id] = {
            "status": "completed",
            "step": "finished",
            "progress": 100
        }
        
        logger.info(f"處理完成: {job_id}, 耗時: {processing_time:.2f}秒")
        
        return ProcessingResponse(
            job_id=job_id,
            status="completed",
            transcript=transcript_result["segments"],
            speaker_count=len(set(
                seg.get("speaker", "UNKNOWN") 
                for seg in transcript_result["segments"]
            )),
            word_segments=transcript_result.get("word_segments", []),
            analysis=analysis,
            processing_time=processing_time,
            language=language,
            analysis_type=analysis_type
        )
        
    except Exception as e:
        logger.error(f"處理音訊時發生錯誤: {e}")
        
        # 更新任務狀態為失敗
        processing_jobs[job_id] = {
            "status": "failed",
            "error": str(e),
            "progress": 0
        }
        
        # 清理可能存在的暫存檔案
        try:
            if 'audio_path' in locals():
                file_handler.cleanup_temp_file(audio_path)
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"處理失敗: {str(e)}")

@app.post("/analyze-transcript")
async def analyze_transcript(
    transcript: list,
    analysis_type: str = "會議摘要"
):
    """分析已有的轉錄文字"""
    try:
        analysis = await openrouter.analyze_transcript(transcript, analysis_type)
        return {
            "status": "completed",
            "analysis": analysis,
            "analysis_type": analysis_type
        }
    except Exception as e:
        logger.error(f"分析轉錄文字時發生錯誤: {e}")
        raise HTTPException(status_code=500, detail=f"分析失敗: {str(e)}")

@app.get("/job/{job_id}/status")
async def get_job_status(job_id: str):
    """查詢任務狀態"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="任務不存在")
    
    return processing_jobs[job_id]

@app.get("/models/available")
async def get_available_models():
    """取得可用的模型列表"""
    return {
        "whisper_models": [
            "tiny", "base", "small", "medium", "large-v2", "large-v3"
        ],
        "supported_languages": [
            {"code": "zh", "name": "中文"},
            {"code": "en", "name": "English"},
            {"code": "ja", "name": "日本語"},
            {"code": "ko", "name": "한국어"}
        ],
        "analysis_types": [
            "會議摘要", "行動項目", "重要決策", "智能分析"
        ]
    }

@app.get("/stats")
async def get_stats():
    """取得系統統計資訊"""
    try:
        import psutil
        
        # 系統資源
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # GPU 資訊（如果可用）
        gpu_info = processor.get_gpu_info()
        
        # 任務統計
        total_jobs = len(processing_jobs)
        completed_jobs = sum(1 for job in processing_jobs.values() if job.get("status") == "completed")
        failed_jobs = sum(1 for job in processing_jobs.values() if job.get("status") == "failed")
        
        return {
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": (disk.used / disk.total) * 100,
                "gpu_info": gpu_info
            },
            "jobs": {
                "total": total_jobs,
                "completed": completed_jobs,
                "failed": failed_jobs,
                "success_rate": (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
            }
        }
    except Exception as e:
        logger.error(f"取得統計資訊時發生錯誤: {e}")
        return {"error": "無法取得統計資訊"}

@app.on_event("startup")
async def startup_event():
    """應用啟動時的初始化"""
    logger.info("🚀 AI Meeting Tool Backend 啟動中...")
    
    # 檢查必要的環境變數
    required_env_vars = ["HF_TOKEN", "OPENROUTER_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"缺少必要的環境變數: {missing_vars}")
        raise RuntimeError(f"請設置環境變數: {missing_vars}")
    
    # 初始化處理器
    try:
        await processor.initialize()
        logger.info("✅ WhisperX 處理器初始化完成")
    except Exception as e:
        logger.error(f"❌ WhisperX 處理器初始化失敗: {e}")
        raise
    
    # 建立必要的目錄
    upload_dir = os.getenv("UPLOAD_DIR", "/tmp/audio_uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    logger.info("🎉 AI Meeting Tool Backend 啟動完成！")

@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉時的清理"""
    logger.info("🛑 AI Meeting Tool Backend 正在關閉...")
    
    # 清理暫存檔案
    file_handler.cleanup_all_temp_files()
    
    # 清理處理器資源
    processor.cleanup()
    
    logger.info("👋 AI Meeting Tool Backend 已關閉")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )