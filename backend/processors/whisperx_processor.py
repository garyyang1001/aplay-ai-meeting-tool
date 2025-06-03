"""
WhisperX 處理器
整合語音轉錄和說話者辨識功能
"""

import whisperx
import torch
import gc
import os
import tempfile
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class WhisperXProcessor:
    def __init__(self, 
                 model_size: str = "base",
                 device: str = "auto",
                 compute_type: str = "float16",
                 language: str = "zh"):
        """
        初始化 WhisperX 處理器
        
        Args:
            model_size: 模型大小 ("tiny", "base", "small", "medium", "large-v2", "large-v3")
            device: 計算設備 ("cpu", "cuda", "auto")
            compute_type: 計算精度 ("float16", "float32", "int8")
            language: 語言代碼 ("zh", "en", "auto")
        """
        self.model_size = model_size
        self.device = self._get_device(device)
        self.compute_type = compute_type
        self.language = language
        self.batch_size = 16
        
        # 檢查 HuggingFace Token
        self.hf_token = os.getenv("HF_TOKEN")
        if not self.hf_token:
            logger.warning("HF_TOKEN not found. Speaker diarization will be disabled.")
        
        # 模型將在第一次使用時加載
        self.model = None
        self.align_model = None
        self.align_metadata = None
        self.diarize_model = None
        
        logger.info(f"WhisperX initialized - Model: {model_size}, Device: {self.device}, Language: {language}")
    
    def _get_device(self, device: str) -> str:
        """智能選擇計算設備"""
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"  # Apple Silicon
            else:
                return "cpu"
        return device
    
    def _load_models(self):
        """延遲加載模型（節省記憶體）"""
        try:
            if self.model is None:
                logger.info(f"Loading Whisper model: {self.model_size}")
                self.model = whisperx.load_model(
                    self.model_size, 
                    self.device, 
                    compute_type=self.compute_type,
                    language=self.language if self.language != "auto" else None
                )
                logger.info("Whisper model loaded successfully")
            
            # 加載對齊模型（用於精確時間戳）
            if self.align_model is None and self.language != "auto":
                try:
                    logger.info("Loading alignment model...")
                    self.align_model, self.align_metadata = whisperx.load_align_model(
                        language_code=self.language, 
                        device=self.device
                    )
                    logger.info("Alignment model loaded successfully")
                except Exception as e:
                    logger.warning(f"Failed to load alignment model: {str(e)}")
            
            # 加載說話者辨識模型
            if self.diarize_model is None and self.hf_token:
                try:
                    logger.info("Loading diarization model...")
                    self.diarize_model = whisperx.DiarizationPipeline(
                        use_auth_token=self.hf_token, 
                        device=self.device
                    )
                    logger.info("Diarization model loaded successfully")
                except Exception as e:
                    logger.warning(f"Failed to load diarization model: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Failed to load models: {str(e)}")
            raise Exception(f"模型加載失敗：{str(e)}")
    
    async def process_meeting_audio(self, 
                                  audio_path: str, 
                                  language: Optional[str] = None,
                                  num_speakers: Optional[int] = None,
                                  min_speakers: Optional[int] = None,
                                  max_speakers: Optional[int] = None) -> Dict[str, Any]:
        """
        處理會議音訊：轉錄 + 說話者辨識
        
        Args:
            audio_path: 音訊檔案路徑
            language: 語言設定（覆蓋預設值）
            num_speakers: 精確說話者數量
            min_speakers: 最少說話者數量
            max_speakers: 最多說話者數量
            
        Returns:
            處理結果包含轉錄和說話者資訊
        """
        try:
            # 加載模型
            self._load_models()
            
            # 使用指定語言或預設語言
            process_language = language or self.language
            
            logger.info(f"Processing audio: {audio_path}")
            start_time = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
            end_time = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
            
            if start_time:
                start_time.record()
            
            # 1. 加載音訊
            audio = whisperx.load_audio(audio_path)
            audio_duration = len(audio) / 16000  # 假設 16kHz
            logger.info(f"Audio duration: {audio_duration:.2f} seconds")
            
            # 2. 語音轉錄
            logger.info("Starting transcription...")
            result = self.model.transcribe(
                audio, 
                batch_size=self.batch_size,
                language=process_language if process_language != "auto" else None
            )
            
            detected_language = result.get("language", process_language)
            logger.info(f"Detected language: {detected_language}")
            
            # 3. 對齊時間戳（如果有對齊模型）
            if self.align_model and self.align_metadata:
                logger.info("Aligning timestamps...")
                try:
                    result = whisperx.align(
                        result["segments"], 
                        self.align_model, 
                        self.align_metadata, 
                        audio, 
                        self.device, 
                        return_char_alignments=False
                    )
                except Exception as e:
                    logger.warning(f"Alignment failed: {str(e)}")
            
            # 4. 說話者辨識
            diarization_info = None
            if self.diarize_model:
                logger.info("Starting speaker diarization...")
                try:
                    # 準備說話者參數
                    diarize_params = {}
                    if num_speakers:
                        diarize_params['num_speakers'] = num_speakers
                    if min_speakers:
                        diarize_params['min_speakers'] = min_speakers
                    if max_speakers:
                        diarize_params['max_speakers'] = max_speakers
                    
                    # 執行說話者辨識
                    diarize_segments = self.diarize_model(
                        audio_path, 
                        **diarize_params
                    )
                    
                    # 將說話者資訊分配給轉錄片段
                    result = whisperx.assign_word_speakers(diarize_segments, result)
                    
                    # 提取說話者統計資訊
                    diarization_info = self._extract_speaker_stats(diarize_segments)
                    logger.info(f"Identified {diarization_info['speaker_count']} speakers")
                    
                except Exception as e:
                    logger.warning(f"Speaker diarization failed: {str(e)}")
            
            # 5. 計算處理時間
            processing_time = None
            if start_time and end_time:
                end_time.record()
                torch.cuda.synchronize()
                processing_time = start_time.elapsed_time(end_time) / 1000  # 轉換為秒
                real_time_factor = processing_time / audio_duration
                logger.info(f"Processing time: {processing_time:.2f}s (RTF: {real_time_factor:.2f}x)")
            
            # 6. 格式化結果
            formatted_result = self._format_result(
                result, 
                diarization_info, 
                audio_duration, 
                processing_time,
                detected_language
            )
            
            # 7. 清理記憶體
            self._cleanup_memory()
            
            logger.info("Audio processing completed successfully")
            return formatted_result
            
        except Exception as e:
            logger.error(f"Audio processing failed: {str(e)}")
            # 確保清理記憶體
            self._cleanup_memory()
            raise Exception(f"音訊處理失敗：{str(e)}")
    
    def _extract_speaker_stats(self, diarization) -> Dict[str, Any]:
        """提取說話者統計資訊"""
        speakers = set()
        speaker_times = {}
        total_speech_time = 0
        
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speakers.add(speaker)
            duration = turn.end - turn.start
            total_speech_time += duration
            
            if speaker not in speaker_times:
                speaker_times[speaker] = 0
            speaker_times[speaker] += duration
        
        # 計算說話時間百分比
        speaker_percentages = {}
        for speaker, time in speaker_times.items():
            speaker_percentages[speaker] = (time / total_speech_time * 100) if total_speech_time > 0 else 0
        
        return {
            "speaker_count": len(speakers),
            "speakers": list(speakers),
            "speaker_times": speaker_times,
            "speaker_percentages": speaker_percentages,
            "total_speech_time": total_speech_time
        }
    
    def _format_result(self, 
                      result: Dict, 
                      diarization_info: Optional[Dict],
                      audio_duration: float,
                      processing_time: Optional[float],
                      detected_language: str) -> Dict[str, Any]:
        """格式化處理結果"""
        
        # 整理轉錄片段
        segments = []
        for segment in result.get("segments", []):
            formatted_segment = {
                "start": round(segment.get("start", 0), 2),
                "end": round(segment.get("end", 0), 2),
                "text": segment.get("text", "").strip(),
                "speaker": segment.get("speaker", "SPEAKER_00")
            }
            
            # 添加詞級對齊資訊（如果有）
            if "words" in segment:
                formatted_segment["words"] = [
                    {
                        "start": round(word.get("start", 0), 2),
                        "end": round(word.get("end", 0), 2),
                        "word": word.get("word", ""),
                        "score": round(word.get("score", 0), 3)
                    }
                    for word in segment["words"]
                ]
            
            segments.append(formatted_segment)
        
        # 構建完整結果
        formatted_result = {
            "segments": segments,
            "metadata": {
                "audio_duration": round(audio_duration, 2),
                "processing_time": round(processing_time, 2) if processing_time else None,
                "real_time_factor": round(processing_time / audio_duration, 2) if processing_time and audio_duration > 0 else None,
                "detected_language": detected_language,
                "model_size": self.model_size,
                "device": self.device
            }
        }
        
        # 添加說話者資訊（如果有）
        if diarization_info:
            formatted_result["diarization"] = diarization_info
        
        return formatted_result
    
    def _cleanup_memory(self):
        """清理 GPU 記憶體"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
    
    async def process_audio_file(self, file_content: bytes, filename: str, **kwargs) -> Dict[str, Any]:
        """處理上傳的音訊檔案"""
        # 創建臨時檔案
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name
        
        try:
            # 處理音訊
            result = await self.process_meeting_audio(tmp_path, **kwargs)
            return result
        finally:
            # 清理臨時檔案
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """獲取模型資訊"""
        return {
            "model_size": self.model_size,
            "device": self.device,
            "compute_type": self.compute_type,
            "language": self.language,
            "cuda_available": torch.cuda.is_available(),
            "models_loaded": {
                "whisper": self.model is not None,
                "alignment": self.align_model is not None,
                "diarization": self.diarize_model is not None
            }
        }
    
    def set_batch_size(self, batch_size: int):
        """動態調整批次大小（用於記憶體優化）"""
        self.batch_size = max(1, min(batch_size, 32))
        logger.info(f"Batch size set to: {self.batch_size}")
