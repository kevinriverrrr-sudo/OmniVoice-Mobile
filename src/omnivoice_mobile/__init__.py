"""
OmniVoice Mobile — Edge TTS for Termux / Android ARM64

Оптимизированный форк k2-fsa/OmniVoice (Xiaomi AI Lab).
600+ языков, клонирование голоса, INT4/INT8 квантизация.

GitHub: https://github.com/kevinriverrrr-sudo/OmniVoice-Mobile
Based on: https://github.com/k2-fsa/OmniVoice (Apache-2.0)
"""

__version__ = "1.0.0"
__author__ = "OmniVoice Mobile Team"
__license__ = "OVPL 1.0"

from omnivoice_mobile.engine import OmniVoiceMobile, get_device_info, optimize_memory

__all__ = ["OmniVoiceMobile", "get_device_info", "optimize_memory"]
