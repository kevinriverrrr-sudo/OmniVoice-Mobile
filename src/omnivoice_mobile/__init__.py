"""
OmniVoice Mobile v2.0 — Edge TTS for Termux / Android ARM64

Оптимизированный форк k2-fsa/OmniVoice (Xiaomi AI Lab).
Полностью переписан на базе Microsoft Edge TTS.
НЕ требует PyTorch, transformers или GPU.

400+ голосов | 75+ языков | Клонирование голоса | 0 ML зависимостей

GitHub: https://github.com/kevinriverrrr-sudo/OmniVoice-Mobile
Based on: https://github.com/k2-fsa/OmniVoice (Apache-2.0)
"""

__version__ = "2.0.0"
__author__ = "OmniVoice Mobile Team"
__license__ = "OVPL 1.0"

from omnivoice_mobile.engine import (
    OmniVoiceMobile,
    VoiceInfo,
    get_device_info,
    list_voices,
    clone_voice,
    design_voice,
)

__all__ = [
    "OmniVoiceMobile",
    "VoiceInfo",
    "get_device_info",
    "list_voices",
    "clone_voice",
    "design_voice",
]
