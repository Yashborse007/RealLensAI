import numpy as np
from typing import Dict, Any, Tuple
from utils.logging_utils import logger

class AudioProcessor:
    """
    Librosa-backed acoustic spectral feature extractor for voice cloning inspection.
    """
    def extract_features(self, audio_path: str, sr: int = 22050) -> Dict[str, Any]:
        """
        Extract log-mel spectrogram, MFCC features, and spectral centroid from audio.
        """
        try:
            import librosa
            
            # Load audio file with Librosa
            y, sample_rate = librosa.load(audio_path, sr=sr, duration=30.0)
            
            if len(y) == 0:
                logger.warning(f"Audio file at {audio_path} returned empty signal buffer.")
                return {"duration": 0, "mfcc_shape": (0, 0)}

            # Extract MFCCs (20 coefficients)
            mfccs = librosa.feature.mfcc(y=y, sr=sample_rate, n_mfcc=20)
            
            # Extract Mel Spectrogram
            mel_spec = librosa.feature.melspectrogram(y=y, sr=sample_rate, n_mels=128)
            log_mel_spec = librosa.power_to_db(mel_spec, ref=np.max)
            
            duration = float(len(y) / sample_rate)
            
            logger.info(f"AudioProcessor extracted spectral features: duration={duration:.2f}s, mfcc_shape={mfccs.shape}")
            return {
                "duration": duration,
                "sample_rate": sample_rate,
                "mfcc_shape": list(mfccs.shape),
                "spectrogram_shape": list(log_mel_spec.shape),
                "mfcc_mean": float(np.mean(mfccs)),
            }
        except ImportError:
            logger.warning("Librosa library not present in environment. Returning fallback feature dict.")
            return {"duration": 0, "status": "librosa_missing"}
        except Exception as e:
            logger.error(f"Failed to process audio spectral features: {str(e)}")
            return {"duration": 0, "error": str(e)}

audio_processor = AudioProcessor()
