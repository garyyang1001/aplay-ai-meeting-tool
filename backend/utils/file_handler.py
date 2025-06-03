import os
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Optional
from fastapi import UploadFile
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class FileHandler:
    """
    檔案處理工具類
    負責上傳檔案的儲存、管理和清理
    """
    
    def __init__(self):
        self.upload_dir = Path(os.getenv('UPLOAD_DIR', '/tmp/audio_uploads'))
        self.max_file_size = int(os.getenv('MAX_FILE_SIZE', 100)) * 1024 * 1024  # MB to bytes
        self.supported_formats = {
            '.mp3', '.wav', '.m4a', '.webm', '.ogg', '.flac', 
            '.aac', '.wma', '.mp4', '.avi', '.mov', '.mkv'
        }
        
        # 確保上傳目錄存在
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"檔案處理器初始化，上傳目錄: {self.upload_dir}")
    
    async def save_uploaded_file(self, file: UploadFile, job_id: str) -> str:
        """
        儲存上傳的檔案
        
        Args:
            file: 上傳的檔案
            job_id: 任務 ID
        
        Returns:
            儲存的檔案路徑
        """
        try:
            # 驗證檔案
            self._validate_file(file)
            
            # 生成檔案名稱
            file_extension = self._get_file_extension(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{job_id}_{timestamp}{file_extension}"
            file_path = self.upload_dir / filename
            
            # 儲存檔案
            logger.info(f"儲存檔案: {filename}")
            
            with open(file_path, 'wb') as f:
                # 分塊讀取避免記憶體問題
                while chunk := await file.read(8192):  # 8KB 塊
                    f.write(chunk)
            
            # 驗證檔案大小
            actual_size = file_path.stat().st_size
            if actual_size > self.max_file_size:
                file_path.unlink()  # 刪除過大的檔案
                raise ValueError(f"檔案大小 {actual_size} 超過限制 {self.max_file_size}")
            
            logger.info(f"檔案儲存成功: {file_path}, 大小: {actual_size} bytes")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"儲存檔案時發生錯誤: {e}")
            raise RuntimeError(f"檔案儲存失敗: {str(e)}")
    
    def _validate_file(self, file: UploadFile):
        """
        驗證上傳檔案
        
        Args:
            file: 上傳的檔案
        
        Raises:
            ValueError: 檔案驗證失敗
        """
        if not file.filename:
            raise ValueError("檔案名稱不能為空")
        
        # 檢查檔案格式
        file_extension = self._get_file_extension(file.filename)
        if file_extension.lower() not in self.supported_formats:
            raise ValueError(
                f"不支援的檔案格式: {file_extension}。"
                f"支援的格式: {', '.join(self.supported_formats)}"
            )
        
        # 檢查檔案大小（粗略檢查）
        if hasattr(file, 'size') and file.size and file.size > self.max_file_size:
            raise ValueError(
                f"檔案大小 {file.size} 超過限制 {self.max_file_size // 1024 // 1024}MB"
            )
    
    def _get_file_extension(self, filename: str) -> str:
        """
        取得檔案副檔名
        
        Args:
            filename: 檔案名稱
        
        Returns:
            檔案副檔名
        """
        return Path(filename).suffix.lower()
    
    def cleanup_temp_file(self, file_path: str):
        """
        清理單個暫存檔案
        
        Args:
            file_path: 檔案路徑
        """
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                path.unlink()
                logger.info(f"清理暫存檔案: {file_path}")
        except Exception as e:
            logger.warning(f"清理暫存檔案失敗: {file_path}, 錯誤: {e}")
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """
        清理過期的暫存檔案
        
        Args:
            max_age_hours: 檔案最大保留時間（小時）
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            cleaned_count = 0
            
            for file_path in self.upload_dir.iterdir():
                if file_path.is_file():
                    # 檢查檔案修改時間
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_mtime < cutoff_time:
                        try:
                            file_path.unlink()
                            cleaned_count += 1
                            logger.debug(f"清理過期檔案: {file_path}")
                        except Exception as e:
                            logger.warning(f"清理檔案失敗: {file_path}, 錯誤: {e}")
            
            if cleaned_count > 0:
                logger.info(f"清理了 {cleaned_count} 個過期檔案")
        
        except Exception as e:
            logger.error(f"清理過期檔案時發生錯誤: {e}")
    
    def cleanup_all_temp_files(self):
        """
        清理所有暫存檔案
        """
        try:
            cleaned_count = 0
            
            for file_path in self.upload_dir.iterdir():
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"清理檔案失敗: {file_path}, 錯誤: {e}")
            
            logger.info(f"清理了 {cleaned_count} 個暫存檔案")
        
        except Exception as e:
            logger.error(f"清理所有暫存檔案時發生錯誤: {e}")
    
    def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        取得檔案資訊
        
        Args:
            file_path: 檔案路徑
        
        Returns:
            檔案資訊字典
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                return None
            
            stat = path.stat()
            
            return {
                'filename': path.name,
                'size': stat.st_size,
                'size_mb': round(stat.st_size / 1024 / 1024, 2),
                'created_time': datetime.fromtimestamp(stat.st_ctime),
                'modified_time': datetime.fromtimestamp(stat.st_mtime),
                'extension': path.suffix.lower(),
                'is_supported': path.suffix.lower() in self.supported_formats
            }
        
        except Exception as e:
            logger.error(f"取得檔案資訊失敗: {file_path}, 錯誤: {e}")
            return None
    
    def get_storage_stats(self) -> dict:
        """
        取得儲存統計資訊
        
        Returns:
            儲存統計字典
        """
        try:
            total_files = 0
            total_size = 0
            file_types = {}
            
            for file_path in self.upload_dir.iterdir():
                if file_path.is_file():
                    total_files += 1
                    file_size = file_path.stat().st_size
                    total_size += file_size
                    
                    # 統計檔案類型
                    ext = file_path.suffix.lower()
                    file_types[ext] = file_types.get(ext, 0) + 1
            
            # 磁碟使用情況
            disk_usage = shutil.disk_usage(self.upload_dir)
            
            return {
                'upload_directory': str(self.upload_dir),
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'file_types': file_types,
                'disk_usage': {
                    'total_gb': round(disk_usage.total / 1024 / 1024 / 1024, 2),
                    'used_gb': round(disk_usage.used / 1024 / 1024 / 1024, 2),
                    'free_gb': round(disk_usage.free / 1024 / 1024 / 1024, 2),
                    'usage_percent': round((disk_usage.used / disk_usage.total) * 100, 1)
                },
                'max_file_size_mb': self.max_file_size // 1024 // 1024,
                'supported_formats': list(self.supported_formats)
            }
        
        except Exception as e:
            logger.error(f"取得儲存統計時發生錯誤: {e}")
            return {'error': str(e)}
    
    def convert_audio_format(
        self, 
        input_path: str, 
        target_format: str = 'wav'
    ) -> str:
        """
        轉換音訊格式（需要 FFmpeg）
        
        Args:
            input_path: 輸入檔案路徑
            target_format: 目標格式
        
        Returns:
            轉換後的檔案路徑
        """
        try:
            import subprocess
            
            input_path = Path(input_path)
            output_path = input_path.with_suffix(f'.{target_format}')
            
            # 使用 FFmpeg 轉換
            cmd = [
                'ffmpeg',
                '-i', str(input_path),
                '-acodec', 'pcm_s16le',  # 16-bit PCM
                '-ar', '16000',  # 16kHz 取樣率
                '-ac', '1',  # 單聲道
                '-y',  # 覆寫輸出檔案
                str(output_path)
            ]
            
            logger.info(f"轉換音訊格式: {input_path} -> {output_path}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 分鐘超時
            )
            
            if result.returncode == 0:
                logger.info(f"音訊轉換成功: {output_path}")
                return str(output_path)
            else:
                logger.error(f"FFmpeg 錯誤: {result.stderr}")
                raise RuntimeError(f"音訊轉換失敗: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            logger.error("音訊轉換超時")
            raise RuntimeError("音訊轉換超時")
        
        except Exception as e:
            logger.error(f"音訊轉換時發生錯誤: {e}")
            raise RuntimeError(f"音訊轉換失敗: {str(e)}")