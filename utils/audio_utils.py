#!/usr/bin/env python3
"""
Минимальный audio processor для OmniVoice Mobile.
Замена громоздкого pydub/librosa на чистый torchaudio + numpy.
"""

import os
import numpy as np


def load_audio(path: str, target_sr: int = 24000) -> np.ndarray:
    """
    Загружает аудио файл и возвращает numpy array (mono, target_sr).
    Поддерживает WAV, FLAC, OGG, MP3 (через torchaudio/ffmpeg).
    """
    import torchaudio

    waveform, sr = torchaudio.load(path)

    # Mono
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    # Resample
    if sr != target_sr:
        resampler = torchaudio.transforms.Resample(sr, target_sr)
        waveform = resampler(waveform)

    return waveform.squeeze(0).numpy()


def save_audio(path: str, audio: np.ndarray, sr: int = 24000):
    """Сохраняет numpy array как WAV файл."""
    import torchaudio
    import torch

    waveform = torch.tensor(audio).unsqueeze(0)  # [1, samples]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    torchaudio.save(path, waveform, sr)


def remove_silence(audio: np.ndarray, sr: int = 24000,
                   threshold_db: float = -40, min_silence_ms: int = 300) -> np.ndarray:
    """Удаляет тишину из аудио."""
    # Вычисляем амплитуду в дБ
    rms = np.sqrt(np.mean(audio ** 2))
    if rms < 1e-10:
        return audio

    db = 20 * np.log10(np.abs(audio) + 1e-10)
    threshold = threshold_db
    is_speech = db > threshold

    # Убираем короткие промежутки тишины
    min_silence_samples = int(min_silence_ms * sr / 1000)
    groups = np.split(is_speech, np.where(np.diff(is_speech.astype(int)) != 0)[0] + 1)

    result = np.zeros_like(audio)
    pos = 0
    for i, group in enumerate(groups):
        if i % 2 == 0:  # речь
            length = len(group)
            if length < min_silence_samples and i > 0 and i < len(groups) - 1:
                # Слишком короткий промежуток — оставляем
                pass
            else:
                end = min(pos + length, len(result))
                result[pos:end] = audio[pos:end]
            pos += length

    # Обрезаем нули в начале и конце
    nonzero = np.nonzero(result)[0]
    if len(nonzero) > 0:
        start = max(0, nonzero[0] - int(0.05 * sr))
        end = min(len(result), nonzero[-1] + int(0.05 * sr))
        result = result[start:end]

    return result


def normalize_audio(audio: np.ndarray, target_db: float = -3.0) -> np.ndarray:
    """Нормализует громкость аудио."""
    rms = np.sqrt(np.mean(audio ** 2))
    if rms < 1e-10:
        return audio

    current_db = 20 * np.log10(rms)
    gain = 10 ** ((target_db - current_db) / 20)

    # Защита от клиппинга
    max_val = np.max(np.abs(audio * gain))
    if max_val > 1.0:
        gain /= max_val

    return audio * gain


def fade_and_pad(audio: np.ndarray, sr: int = 24000,
                 fade_ms: int = 10, pad_ms: int = 50) -> np.ndarray:
    """Добавляет fade in/out и silence padding."""
    fade_samples = int(fade_ms * sr / 1000)
    pad_samples = int(pad_ms * sr / 1000)

    # Fade in
    if fade_samples > 0 and len(audio) > fade_samples:
        fade_curve = np.linspace(0, 1, fade_samples)
        audio[:fade_samples] *= fade_curve

    # Fade out
    if fade_samples > 0 and len(audio) > fade_samples:
        fade_curve = np.linspace(1, 0, fade_samples)
        audio[-fade_samples:] *= fade_curve

    # Padding
    padding = np.zeros(pad_samples)
    return np.concatenate([padding, audio, padding])


def prepare_ref_audio(path: str, target_sr: int = 24000,
                      max_duration: float = 10.0) -> np.ndarray:
    """
    Подготавливает референсное аудио для клонирования голоса.
    Обрезает до max_duration, нормализует, добавляет fade.
    """
    audio = load_audio(path, target_sr)

    # Обрезаем до максимальной длины
    max_samples = int(max_duration * target_sr)
    if len(audio) > max_samples:
        audio = audio[:max_samples]

    # Нормализуем
    audio = normalize_audio(audio, target_db=-6.0)

    # Добавляем fade
    audio = fade_and_pad(audio, target_sr, fade_ms=5, pad_ms=20)

    return audio
