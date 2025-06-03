#!/usr/bin/env python3
"""
WhisperX 測試腳本
用於驗證 WhisperX 安裝和基本功能
"""

import os
import sys
import logging
import tempfile
from pathlib import Path

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """測試必要模組導入"""
    logger.info("🔍 測試模組導入...")
    
    try:
        import torch
        logger.info(f"✅ PyTorch 版本: {torch.__version__}")
        
        import whisperx
        logger.info("✅ WhisperX 導入成功")
        
        # 檢查 CUDA
        cuda_available = torch.cuda.is_available()
        logger.info(f"🖥️  CUDA 可用: {cuda_available}")
        
        if cuda_available:
            logger.info(f"📊 GPU 數量: {torch.cuda.device_count()}")
            logger.info(f"🎯 當前 GPU: {torch.cuda.get_device_name()}")
        
        # 檢查 MPS (Apple Silicon)
        if hasattr(torch.backends, 'mps'):
            mps_available = torch.backends.mps.is_available()
            logger.info(f"🍎 MPS 可用: {mps_available}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 模組導入失敗: {e}")
        return False

def test_whisper_model():
    """測試 Whisper 模型載入"""
    logger.info("🔍 測試 Whisper 模型載入...")
    
    try:
        import whisperx
        import torch
        
        # 自動選擇設備
        if torch.cuda.is_available():
            device = "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        
        logger.info(f"📱 使用設備: {device}")
        
        # 載入較小的模型進行測試
        model = whisperx.load_model("tiny", device)
        logger.info("✅ Whisper 模型載入成功")
        
        # 清理
        del model
        if device == "cuda":
            torch.cuda.empty_cache()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Whisper 模型載入失敗: {e}")
        return False

def test_diarization():
    """測試說話者辨識"""
    logger.info("🔍 測試說話者辨識...")
    
    hf_token = os.getenv('HF_TOKEN')
    if not hf_token:
        logger.warning("⚠️  未設定 HF_TOKEN，跳過說話者辨識測試")
        return True
    
    try:
        import whisperx
        import torch
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 載入說話者辨識模型
        diarize_model = whisperx.DiarizationPipeline(
            use_auth_token=hf_token,
            device=device
        )
        logger.info("✅ 說話者辨識模型載入成功")
        
        # 清理
        del diarize_model
        if device == "cuda":
            torch.cuda.empty_cache()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 說話者辨識模型載入失敗: {e}")
        logger.error("請確保已接受 HuggingFace 模型使用條款:")
        logger.error("- https://huggingface.co/pyannote/speaker-diarization-3.1")
        logger.error("- https://huggingface.co/pyannote/segmentation-3.0")
        return False

def test_audio_processing():
    """測試音訊處理（如果有測試檔案）"""
    logger.info("🔍 測試音訊處理...")
    
    # 尋找測試音訊檔案
    test_files = [
        "test_audio.wav",
        "sample.wav", 
        "test.mp3",
        "../test_audio.wav"
    ]
    
    test_file = None
    for file_path in test_files:
        if Path(file_path).exists():
            test_file = file_path
            break
    
    if not test_file:
        logger.warning("⚠️  未找到測試音訊檔案，跳過音訊處理測試")
        logger.info("💡 你可以放置一個 test_audio.wav 檔案來測試完整功能")
        return True
    
    try:
        import whisperx
        import torch
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"🎵 處理測試檔案: {test_file}")
        
        # 載入模型
        model = whisperx.load_model("tiny", device)
        
        # 載入音訊
        audio = whisperx.load_audio(test_file)
        logger.info(f"📊 音訊時長: {len(audio)/16000:.2f} 秒")
        
        # 轉錄
        result = model.transcribe(audio, batch_size=4)
        logger.info(f"📝 轉錄片段數: {len(result['segments'])}")
        
        # 顯示第一個片段
        if result['segments']:
            first_segment = result['segments'][0]
            logger.info(f"📖 第一個片段: {first_segment['text'][:50]}...")
        
        logger.info("✅ 音訊處理測試成功")
        
        # 清理
        del model
        if device == "cuda":
            torch.cuda.empty_cache()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 音訊處理測試失敗: {e}")
        return False

def test_environment():
    """測試環境設定"""
    logger.info("🔍 檢查環境設定...")
    
    # 檢查環境變數
    hf_token = os.getenv('HF_TOKEN')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    
    logger.info(f"🔑 HF_TOKEN: {'✅ 已設定' if hf_token else '❌ 未設定'}")
    logger.info(f"🔑 OPENROUTER_API_KEY: {'✅ 已設定' if openrouter_key else '❌ 未設定'}")
    
    # 檢查必要目錄
    upload_dir = os.getenv('UPLOAD_DIR', '/tmp/audio_uploads')
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 上傳目錄: {upload_dir}")
    
    # 檢查 FFmpeg
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            logger.info("✅ FFmpeg 可用")
        else:
            logger.warning("⚠️  FFmpeg 不可用")
    except:
        logger.warning("⚠️  FFmpeg 不可用")
    
    return True

def main():
    """主測試函數"""
    logger.info("🚀 開始 WhisperX 測試")
    logger.info("=" * 50)
    
    tests = [
        ("模組導入", test_imports),
        ("環境設定", test_environment),
        ("Whisper 模型", test_whisper_model),
        ("說話者辨識", test_diarization),
        ("音訊處理", test_audio_processing)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 {test_name} 測試:")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"測試 {test_name} 時發生未預期錯誤: {e}")
            results.append((test_name, False))
    
    # 顯示測試結果
    logger.info("\n" + "=" * 50)
    logger.info("📊 測試結果摘要:")
    
    for test_name, success in results:
        status = "✅ 通過" if success else "❌ 失敗"
        logger.info(f"  {test_name}: {status}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    logger.info(f"\n🎯 總結: {passed}/{total} 項測試通過")
    
    if passed == total:
        logger.info("🎉 所有測試通過！WhisperX 已準備就緒。")
        return 0
    else:
        logger.warning("⚠️  部分測試失敗，請檢查上述錯誤訊息。")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)