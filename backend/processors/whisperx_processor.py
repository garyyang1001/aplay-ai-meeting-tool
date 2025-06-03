import os
import torch
import whisperx
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)

class WhisperXProcessor:
    """
    WhisperX 音訊處理器
    整合語音轉錄和說話者辨識功能
    """
    
    def __init__(self):
        self.device = self._get_device()
        self.batch_size = int(os.getenv('BATCH_SIZE', 16))
        self.compute_type = os.getenv('COMPUTE_TYPE', 'float16')
        self.model_size = os.getenv('DEFAULT_MODEL_SIZE', 'large-v2')
        
        # 模型快取
        self.whisper_model = None
        self.align_models = {}  # 語言特定的對齊模型
        self.diarization_pipeline = None
        
        logger.info(f"WhisperX 處理器初始化：設備={self.device}, 模型={self.model_size}")
    
    def _get_device(self) -> str:
        """自動偵測最佳設備"""
        device_setting = os.getenv('DEVICE', 'auto')
        
        if device_setting == 'auto':
            if torch.cuda.is_available():
                return 'cuda'
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return 'mps'  # Apple Silicon GPU
            else:
                return 'cpu'
        
        return device_setting
    
    async def initialize(self):
        """初始化處理器和模型"""
        try:
            # 預載入 Whisper 模型
            logger.info(f"載入 Whisper 模型: {self.model_size}")
            self.whisper_model = whisperx.load_model(
                self.model_size,
                self.device,
                compute_type=self.compute_type
            )
            
            # 預載入說話者辨識模型
            hf_token = os.getenv('HF_TOKEN')
            if hf_token:
                logger.info("載入說話者辨識模型")
                self.diarization_pipeline = whisperx.DiarizationPipeline(
                    use_auth_token=hf_token,
                    device=self.device
                )
            else:
                logger.warning("未設定 HF_TOKEN，說話者辨識功能將無法使用")
            
            logger.info("✅ WhisperX 處理器初始化完成")
            
        except Exception as e:
            logger.error(f"❌ WhisperX 處理器初始化失敗: {e}")
            raise
    
    def is_ready(self) -> bool:
        """檢查處理器是否就緒"""
        return self.whisper_model is not None
    
    def health_check(self) -> Dict[str, Union[str, bool]]:
        """健康檢查"""
        try:
            # 檢查模型狀態
            model_ready = self.whisper_model is not None
            diarization_ready = self.diarization_pipeline is not None
            
            # 檢查 GPU 記憶體（如果使用 GPU）
            gpu_info = self.get_gpu_info()
            
            return {
                "status": "ready" if model_ready else "not_ready",
                "whisper_model": model_ready,
                "diarization": diarization_ready,
                "device": self.device,
                "gpu_info": gpu_info
            }
        except Exception as e:
            logger.error(f"健康檢查失敗: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_gpu_info(self) -> Optional[Dict]:
        """取得 GPU 資訊"""
        try:
            if self.device == 'cuda' and torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                current_device = torch.cuda.current_device()
                
                return {
                    "available": True,
                    "device_count": gpu_count,
                    "current_device": current_device,
                    "device_name": torch.cuda.get_device_name(current_device),
                    "memory_allocated": torch.cuda.memory_allocated(current_device),
                    "memory_reserved": torch.cuda.memory_reserved(current_device)
                }
            return {"available": False, "reason": "CUDA not available"}
        except Exception as e:
            return {"available": False, "error": str(e)}
    
    def process_meeting_audio(
        self, 
        audio_path: str, 
        language: str = "zh",
        num_speakers: Optional[int] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None
    ) -> Dict:
        """
        處理會議音訊：轉錄 + 說話者辨識
        
        Args:
            audio_path: 音訊檔案路徑
            language: 語言代碼 (zh, en, ja, ko)
            num_speakers: 固定說話者數量
            min_speakers: 最少說話者數量
            max_speakers: 最多說話者數量
        
        Returns:
            處理結果字典
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"開始處理音訊: {audio_path}, 語言: {language}")
            
            # 1. 載入音訊
            audio = whisperx.load_audio(audio_path)
            audio_duration = len(audio) / 16000  # 假設 16kHz 採樣率
            
            logger.info(f"音訊時長: {audio_duration:.2f} 秒")
            
            # 2. 語音轉錄
            logger.info("開始語音轉錄...")
            result = self.whisper_model.transcribe(
                audio,
                batch_size=self.batch_size,
                language=language
            )
            
            # 3. 詞級對齊
            logger.info("開始詞級對齊...")
            align_model, metadata = self._get_align_model(language)
            
            if align_model:
                result = whisperx.align(
                    result["segments"],
                    align_model,
                    metadata,
                    audio,
                    self.device,
                    return_char_alignments=False
                )
            
            # 4. 說話者辨識
            if self.diarization_pipeline:
                logger.info("開始說話者辨識...")
                
                # 設定說話者參數
                diarization_params = {}
                if num_speakers:
                    diarization_params['num_speakers'] = num_speakers
                if min_speakers:
                    diarization_params['min_speakers'] = min_speakers
                if max_speakers:
                    diarization_params['max_speakers'] = max_speakers
                
                diarize_segments = self.diarization_pipeline(
                    audio, **diarization_params
                )
                
                # 分配說話者標籤
                result = whisperx.assign_word_speakers(
                    diarize_segments, result
                )
            else:
                logger.warning("說話者辨識不可用，跳過此步驟")
            
            # 5. 處理結果
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 計算說話者統計
            segments = result.get("segments", [])
            speakers = set()
            for segment in segments:
                if "speaker" in segment and segment["speaker"]:
                    speakers.add(segment["speaker"])
            
            logger.info(f"處理完成，耗時: {processing_time:.2f}秒, 發現 {len(speakers)} 位說話者")
            
            return {
                "segments": segments,
                "word_segments": result.get("word_segments", []),
                "language": language,
                "audio_duration": audio_duration,
                "processing_time": processing_time,
                "speaker_count": len(speakers),
                "speakers": list(speakers),
                "real_time_factor": processing_time / audio_duration if audio_duration > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"處理音訊時發生錯誤: {e}")
            raise RuntimeError(f"音訊處理失敗: {str(e)}")
    
    def _get_align_model(self, language: str):
        """取得或載入語言特定的對齊模型"""
        try:
            if language not in self.align_models:
                logger.info(f"載入 {language} 對齊模型")
                model, metadata = whisperx.load_align_model(
                    language_code=language,
                    device=self.device
                )
                self.align_models[language] = (model, metadata)
            
            return self.align_models[language]
        except Exception as e:
            logger.warning(f"無法載入 {language} 對齊模型: {e}")
            return None, None
    
    def process_audio_chunk(
        self, 
        audio_chunk: bytes, 
        language: str = "zh"
    ) -> Dict:
        """
        處理音訊片段（用於即時處理）
        
        Args:
            audio_chunk: 音訊片段位元組
            language: 語言代碼
        
        Returns:
            部分處理結果
        """
        try:
            # 這裡可以實作即時處理邏輯
            # 目前簡化為呼叫完整處理
            # 實際實作需要音訊緩衝區管理
            
            logger.info("處理音訊片段（簡化實作）")
            
            return {
                "status": "chunk_processed",
                "partial_result": [],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"處理音訊片段時發生錯誤: {e}")
            raise RuntimeError(f"音訊片段處理失敗: {str(e)}")
    
    def estimate_processing_time(self, audio_duration: float) -> float:
        """
        估算處理時間
        
        Args:
            audio_duration: 音訊時長（秒）
        
        Returns:
            預估處理時間（秒）
        """
        # 基於經驗的估算公式
        base_factor = 0.05  # 基礎處理係數
        
        if self.device == 'cuda':
            device_factor = 1.0
        elif self.device == 'mps':
            device_factor = 1.5
        else:
            device_factor = 3.0
        
        model_factor = {
            'tiny': 0.5,
            'base': 0.7,
            'small': 1.0,
            'medium': 1.5,
            'large-v2': 2.0,
            'large-v3': 2.2
        }.get(self.model_size, 2.0)
        
        estimated_time = audio_duration * base_factor * device_factor * model_factor
        
        return max(estimated_time, 5.0)  # 最少 5 秒處理時間
    
    def cleanup(self):
        """
        清理資源
        """
        try:
            # 清理 GPU 記憶體
            if self.device == 'cuda' and torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # 重置模型引用
            self.whisper_model = None
            self.align_models.clear()
            self.diarization_pipeline = None
            
            logger.info("🧹 WhisperX 處理器資源清理完成")
            
        except Exception as e:
            logger.error(f"清理資源時發生錯誤: {e}")
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """
        取得支援的語言列表
        """
        return [
            {"code": "zh", "name": "中文", "whisper_support": True, "align_support": True},
            {"code": "en", "name": "English", "whisper_support": True, "align_support": True},
            {"code": "ja", "name": "日本語", "whisper_support": True, "align_support": True},
            {"code": "ko", "name": "한국어", "whisper_support": True, "align_support": False},
            {"code": "es", "name": "Español", "whisper_support": True, "align_support": True},
            {"code": "fr", "name": "Français", "whisper_support": True, "align_support": True},
            {"code": "de", "name": "Deutsch", "whisper_support": True, "align_support": True},
            {"code": "it", "name": "Italiano", "whisper_support": True, "align_support": True},
            {"code": "pt", "name": "Português", "whisper_support": True, "align_support": True}
        ]