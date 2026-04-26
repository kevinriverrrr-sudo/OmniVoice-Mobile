"""
OmniVoice Mobile v2.1 — Edge TTS for Termux / Android ARM64

Русский язык по умолчанию. 150+ пресетов голосов. Клонирование голоса.
НЕ требует PyTorch. Работает на ЛЮБОМ Termux.

Автор: kevinriverrrr-sudo (GitHub)
Репозиторий: https://github.com/kevinriverrrr-sudo/OmniVoice-Mobile
На базе: https://github.com/k2-fsa/OmniVoice (Apache-2.0)
"""

__version__ = "2.1.0"
__author__ = "kevinriverrrr-sudo"
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
