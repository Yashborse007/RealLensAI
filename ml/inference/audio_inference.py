from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

import librosa
import numpy as np
import torch

from ml.config import AUDIO_DECISION_THRESHOLD, AUDIO_SAMPLE_RATE, get_torch_device
from ml.models.audio.aasist_model import AASISTAudioDetector


def _load_and_validate_audio(file_path: str) -> Tuple[np.ndarray, int]:
    try:
        waveform, sample_rate = librosa.load(file_path, sr=AUDIO_SAMPLE_RATE, mono=True, res_type="kaiser_fast")
    except Exception as exc:  # pragma: no cover - runtime validation path
        raise ValueError(f"Could not read audio file '{file_path}': {exc}")

    if waveform is None or waveform.size == 0:
        raise ValueError(f"Audio file '{file_path}' did not contain readable samples.")

    waveform = np.nan_to_num(waveform, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    if not np.isfinite(waveform).all():
        waveform = np.nan_to_num(waveform)

    if waveform.std() < 1e-6:
        raise ValueError(f"Audio file '{file_path}' is effectively silent; no meaningful audio signal was detected.")

    return waveform, int(sample_rate)


def _extract_audio_features(waveform: np.ndarray, sample_rate: int) -> Dict[str, float]:
    waveform = librosa.util.normalize(waveform)
    waveform = librosa.effects.trim(waveform, top_db=30)[0]
    if waveform.size == 0:
        waveform = np.zeros(1, dtype=np.float32)

    stft = np.abs(librosa.stft(waveform, n_fft=512, hop_length=160, win_length=400))
    mel = librosa.feature.melspectrogram(
        y=waveform,
        sr=sample_rate,
        n_fft=512,
        hop_length=160,
        n_mels=64,
        fmin=50,
        fmax=min(sample_rate / 2, 8000),
    )
    log_mel = librosa.power_to_db(mel, ref=np.max)
    mfcc = librosa.feature.mfcc(S=librosa.power_to_db(mel), n_mfcc=20)

    spectral_centroid = float(librosa.feature.spectral_centroid(y=waveform, sr=sample_rate, n_fft=512, hop_length=160).mean() / max(sample_rate, 1))
    spectral_rolloff = float(librosa.feature.spectral_rolloff(y=waveform, sr=sample_rate, n_fft=512, hop_length=160).mean() / max(sample_rate, 1))
    spectral_flatness = float(librosa.feature.spectral_flatness(y=waveform, n_fft=512, hop_length=160).mean())
    mfcc_std = float(mfcc.std())
    energy = float(np.mean(np.abs(waveform)))

    return {
        "spectral_centroid": spectral_centroid,
        "spectral_rolloff": spectral_rolloff,
        "spectral_flatness": spectral_flatness,
        "mfcc_std": mfcc_std,
        "log_mel_mean": float(log_mel.mean()),
        "energy": energy,
    }


def _heuristic_audio_probability(waveform: np.ndarray, sample_rate: int) -> float:
    features = _extract_audio_features(waveform, sample_rate)
    score = (
        0.35 * np.clip(features["spectral_flatness"], 0.0, 1.0)
        + 0.25 * np.clip(features["spectral_centroid"], 0.0, 1.0)
        + 0.20 * np.clip(features["spectral_rolloff"], 0.0, 1.0)
        + 0.20 * np.clip(features["mfcc_std"] / 40.0, 0.0, 1.0)
    )
    return float(np.clip(score, 0.0, 1.0))


def predict_audio_probability(
    file_path: str,
    model: Optional[AASISTAudioDetector] = None,
    threshold: float = AUDIO_DECISION_THRESHOLD,
) -> Dict[str, Any]:
    """Analyze a single audio file with feature extraction and a lightweight spectral model fallback.

    Frequency and spectral patterns are treated as supporting evidence, not forensic proof.
    """
    started_at = time.perf_counter()
    model_was_provided = model is not None

    try:
        waveform, sample_rate = _load_and_validate_audio(file_path)
    except ValueError as exc:
        return {
            "success": False,
            "audio_available": False,
            "media_type": "audio",
            "prediction": {"label": "REAL", "confidence": 0.0},
            "label": "REAL",
            "confidence": 0.0,
            "duration": 0.0,
            "sample_rate": 0,
            "processing_time_ms": int((time.perf_counter() - started_at) * 1000),
            "status": "INVALID_AUDIO",
            "model": "mel-mfcc-supporting-evidence",
            "threshold": float(threshold),
            "message": str(exc),
        }

    if model is None:
        model = AASISTAudioDetector()
        load_status = model.load_checkpoint()

    reusable_model = model is not None and (
        model_was_provided or load_status.get("success")
    )
    probability = _heuristic_audio_probability(waveform, sample_rate)

    if reusable_model and load_status.get("success"):
        max_len = int(sample_rate * 10)
        if waveform.shape[0] > max_len:
            waveform = waveform[:max_len]
        if waveform.shape[0] < max_len:
            waveform = np.pad(waveform, (0, max_len - waveform.shape[0]), mode="constant")
        tensor = torch.from_numpy(waveform.astype(np.float32)).unsqueeze(0).unsqueeze(0).to(get_torch_device())
        with torch.no_grad():
            probability = float(torch.sigmoid(model(tensor)).squeeze(0).item())
        model_name = "AASIST"
    else:
        model_name = "mel-mfcc-supporting-evidence"

    probability = float(np.clip(probability, 0.0, 1.0))
    label = "FAKE" if probability >= threshold else "REAL"
    confidence = probability if label == "FAKE" else 1.0 - probability

    return {
        "success": True,
        "audio_available": True,
        "media_type": "audio",
        "prediction": {
            "label": label,
            "confidence": float(max(0.0, min(1.0, confidence))),
        },
        "label": label,
        "confidence": float(max(0.0, min(1.0, confidence))),
        "duration": float(round(len(waveform) / sample_rate, 4)),
        "sample_rate": int(sample_rate),
        "processing_time_ms": int((time.perf_counter() - started_at) * 1000),
        "status": "COMPLETED",
        "model": model_name,
        "threshold": float(threshold),
        "message": "Audio score is supporting evidence only and should not be treated as proof of deepfake activity.",
    }
