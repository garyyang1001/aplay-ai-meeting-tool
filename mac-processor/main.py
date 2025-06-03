#!/usr/bin/env python3
"""
Mac Mini 音頻處理服務
使用 pyannote.audio 進行說話者識別，提供給前端調用
"""

import os
import tempfile
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
import uuid
import json

import httpx
import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore

# 嘗試導入 pyannote
try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False
    logging.warning("pyannote.audio 未安裝，將僅提供基礎音頻處理功能")

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI 應用
app = FastAPI(
    title="AI 會議工具 - Mac Mini 處理服務",
    description="提供音頻處理、說話者識別和增強分析功能",
    version="1.0.0"
)

# CORS 設置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境請限制為特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 資料模型
class ProcessRequest(BaseModel):
    job_id: str
    audio_url: str
    transcript: Optional[List[Dict]] = None
    num_speakers: Optional[int] = None
    analysis_type: str = "會議摘要"
    
class ProcessResult(BaseModel):
    job_id: str
    status: str
    speakers: Optional[List[Dict]] = None
    enhanced_transcript: Optional[List[Dict]] = None
    error: Optional[str] = None

# 全域變數
diarization_pipeline = None
firebase_db = None
processing_jobs = {}  # 儲存處理中的任務

class AudioProcessor:
    """音頻處理核心類別"""
    
    def __init__(self):
        self.setup_pyannote()
        self.setup_firebase()
    
    def setup_pyannote(self):
        """設置 pyannote pipeline"""
        global diarization_pipeline
        
        if not PYANNOTE_AVAILABLE:
            logger.warning("Pyannote 不可用，跳過初始化")
            return
        
        try:
            hf_token = os.getenv("HF_TOKEN")
            if not hf_token:
                logger.error("請設置 HF_TOKEN 環境變數")
                return
            
            logger.info("正在載入 pyannote pipeline...")
            diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=hf_token
            )
            logger.info("Pyannote pipeline 載入成功")
            
        except Exception as e:
            logger.error(f"Pyannote 初始化失敗: {e}")
            diarization_pipeline = None
    
    def setup_firebase(self):
        """設置 Firebase 連接"""
        global firebase_db
        
        try:
            # 檢查 Firebase 配置
            firebase_config = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
            if firebase_config:
                # 從環境變數載入服務帳戶金鑰
                cred_dict = json.loads(firebase_config)
                cred = credentials.Certificate(cred_dict)
            else:
                # 嘗試從檔案載入
                cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                else:
                    logger.warning("Firebase 配置未找到，僅使用本地處理")
                    return
            
            # 初始化 Firebase
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
            
            firebase_db = firestore.client()
            logger.info("Firebase 連接成功")
            
        except Exception as e:
            logger.error(f"Firebase 初始化失敗: {e}")
            firebase_db = None
    
    async def download_audio(self, audio_url: str) -> str:
        """下載音頻檔案"""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.get(audio_url)
                response.raise_for_status()
                
                # 建立臨時檔案
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                temp_file.write(response.content)
                temp_file.close()
                
                logger.info(f"音頻檔案下載完成: {temp_file.name}")
                return temp_file.name
                
        except Exception as e:
            logger.error(f"音頻下載失敗: {e}")
            raise HTTPException(status_code=400, detail=f"音頻下載失敗: {e}")
    
    def process_diarization(self, audio_path: str, num_speakers: Optional[int] = None) -> List[Dict]:
        """執行說話者識別"""
        if not diarization_pipeline:
            logger.warning("Pyannote 不可用，返回模擬結果")
            return [
                {
                    "speaker": "SPEAKER_00",
                    "start": 0.0,
                    "end": 30.0,
                    "duration": 30.0
                }
            ]
        
        try:
            logger.info("開始說話者識別...")
            
            # 設置參數
            params = {}
            if num_speakers:
                params['num_speakers'] = num_speakers
            
            # 執行識別
            diarization = diarization_pipeline(audio_path, **params)
            
            # 轉換結果
            results = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                results.append({
                    "speaker": speaker,
                    "start": turn.start,
                    "end": turn.end,
                    "duration": turn.end - turn.start
                })
            
            logger.info(f"說話者識別完成，找到 {len(set(r['speaker'] for r in results))} 位說話者")
            return results
            
        except Exception as e:
            logger.error(f"說話者識別失敗: {e}")
            # 返回預設結果
            return [
                {
                    "speaker": "SPEAKER_00",
                    "start": 0.0,
                    "end": 60.0,
                    "duration": 60.0
                }
            ]
    
    def align_transcript_with_speakers(
        self, 
        transcript: List[Dict], 
        diarization: List[Dict]
    ) -> List[Dict]:
        """將轉錄文字與說話者對齊"""
        if not transcript:
            return []
        
        enhanced = []
        
        for entry in transcript:
            timestamp = entry.get('timestamp', 0) / 1000.0  # 轉為秒
            text = entry.get('text', '')
            
            # 找出對應的說話者
            speaker = "UNKNOWN"
            for seg in diarization:
                if seg['start'] <= timestamp <= seg['end']:
                    speaker = seg['speaker']
                    break
            
            enhanced.append({
                "text": text,
                "speaker": speaker,
                "timestamp": timestamp,
                "enhanced": True
            })
        
        return enhanced
    
    async def update_firebase_result(self, job_id: str, result: Dict):
        """更新 Firebase 結果"""
        if not firebase_db:
            logger.warning("Firebase 不可用，跳過結果更新")
            return
        
        try:
            doc_ref = firebase_db.collection('processing_jobs').document(job_id)
            await asyncio.get_event_loop().run_in_executor(
                None, 
                doc_ref.set, 
                {
                    **result,
                    'updated_at': datetime.now(),
                    'processed_by': 'mac-mini'
                }
            )
            logger.info(f"Firebase 結果已更新: {job_id}")
            
        except Exception as e:
            logger.error(f"Firebase 更新失敗: {e}")

# 初始化處理器
processor = AudioProcessor()

@app.get("/")
async def root():
    """健康檢查端點"""
    return {
        "service": "AI 會議工具 - Mac Mini 處理服務",
        "status": "running",
        "pyannote_available": PYANNOTE_AVAILABLE,
        "firebase_available": firebase_db is not None,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """詳細健康檢查"""
    return {
        "status": "healthy",
        "services": {
            "pyannote": PYANNOTE_AVAILABLE,
            "firebase": firebase_db is not None,
            "processing_jobs": len(processing_jobs)
        },
        "system": {
            "timestamp": datetime.now().isoformat(),
            "temp_dir": tempfile.gettempdir()
        }
    }

@app.post("/process")
async def process_audio(
    request: ProcessRequest,
    background_tasks: BackgroundTasks
):
    """接收前端的音頻處理請求"""
    job_id = request.job_id
    
    # 記錄任務開始
    processing_jobs[job_id] = {
        "status": "processing",
        "started_at": datetime.now(),
        "audio_url": request.audio_url
    }
    
    # 背景處理任務
    background_tasks.add_task(
        handle_audio_processing,
        job_id,
        request.audio_url,
        request.transcript,
        request.num_speakers
    )
    
    logger.info(f"接收到處理請求: {job_id}")
    
    return {
        "status": "processing",
        "job_id": job_id,
        "message": "音頻處理已開始"
    }

@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """查詢任務狀態"""
    if job_id in processing_jobs:
        return processing_jobs[job_id]
    
    # 嘗試從 Firebase 查詢
    if firebase_db:
        try:
            doc_ref = firebase_db.collection('processing_jobs').document(job_id)
            doc = await asyncio.get_event_loop().run_in_executor(None, doc_ref.get)
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            logger.error(f"Firebase 查詢失敗: {e}")
    
    raise HTTPException(status_code=404, detail="任務未找到")

@app.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    num_speakers: Optional[int] = None,
    background_tasks: BackgroundTasks = None
):
    """直接上傳音頻檔案處理"""
    # 生成任務ID
    job_id = f"upload_{uuid.uuid4().hex[:8]}"
    
    try:
        # 保存上傳的檔案
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        # 記錄任務
        processing_jobs[job_id] = {
            "status": "processing",
            "started_at": datetime.now(),
            "audio_path": temp_file.name
        }
        
        # 背景處理
        background_tasks.add_task(
            handle_uploaded_audio_processing,
            job_id,
            temp_file.name,
            num_speakers
        )
        
        return {
            "status": "processing",
            "job_id": job_id,
            "message": "音頻上傳成功，處理中"
        }
        
    except Exception as e:
        logger.error(f"檔案上傳失敗: {e}")
        raise HTTPException(status_code=400, detail=f"檔案上傳失敗: {e}")

async def handle_audio_processing(
    job_id: str,
    audio_url: str,
    transcript: Optional[List[Dict]] = None,
    num_speakers: Optional[int] = None
):
    """處理音頻的背景任務"""
    try:
        logger.info(f"開始處理任務 {job_id}")
        
        # 下載音頻
        processing_jobs[job_id]["status"] = "downloading"
        audio_path = await processor.download_audio(audio_url)
        
        # 執行說話者識別
        processing_jobs[job_id]["status"] = "diarizing"
        diarization = processor.process_diarization(audio_path, num_speakers)
        
        # 對齊轉錄文字（如果有）
        enhanced_transcript = None
        if transcript:
            enhanced_transcript = processor.align_transcript_with_speakers(
                transcript, diarization
            )
        
        # 準備結果
        result = {
            "job_id": job_id,
            "status": "completed",
            "speakers": diarization,
            "enhanced_transcript": enhanced_transcript,
            "speaker_count": len(set(seg['speaker'] for seg in diarization)),
            "total_duration": max(seg['end'] for seg in diarization) if diarization else 0
        }
        
        # 更新本地狀態
        processing_jobs[job_id] = {
            **processing_jobs[job_id],
            **result,
            "completed_at": datetime.now()
        }
        
        # 更新 Firebase
        await processor.update_firebase_result(job_id, result)
        
        # 清理臨時檔案
        if os.path.exists(audio_path):
            os.unlink(audio_path)
        
        logger.info(f"任務 {job_id} 處理完成")
        
    except Exception as e:
        logger.error(f"任務 {job_id} 處理失敗: {e}")
        
        # 更新錯誤狀態
        error_result = {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now()
        }
        
        processing_jobs[job_id] = {
            **processing_jobs.get(job_id, {}),
            **error_result
        }
        
        await processor.update_firebase_result(job_id, error_result)

async def handle_uploaded_audio_processing(
    job_id: str,
    audio_path: str,
    num_speakers: Optional[int] = None
):
    """處理直接上傳音頻的背景任務"""
    try:
        logger.info(f"開始處理上傳任務 {job_id}")
        
        # 執行說話者識別
        processing_jobs[job_id]["status"] = "diarizing"
        diarization = processor.process_diarization(audio_path, num_speakers)
        
        # 準備結果
        result = {
            "job_id": job_id,
            "status": "completed",
            "speakers": diarization,
            "speaker_count": len(set(seg['speaker'] for seg in diarization)),
            "total_duration": max(seg['end'] for seg in diarization) if diarization else 0
        }
        
        # 更新本地狀態
        processing_jobs[job_id] = {
            **processing_jobs[job_id],
            **result,
            "completed_at": datetime.now()
        }
        
        # 清理臨時檔案
        if os.path.exists(audio_path):
            os.unlink(audio_path)
        
        logger.info(f"上傳任務 {job_id} 處理完成")
        
    except Exception as e:
        logger.error(f"上傳任務 {job_id} 處理失敗: {e}")
        
        error_result = {
            "job_id": job_id,
            "status": "failed",
            "error": str(e)
        }
        
        processing_jobs[job_id] = {
            **processing_jobs.get(job_id, {}),
            **error_result
        }

if __name__ == "__main__":
    # 啟動服務
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"啟動 Mac Mini 處理服務在 {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
