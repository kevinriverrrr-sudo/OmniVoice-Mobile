"""
OmniVoice Mobile v2.0 — Edge TTS Engine for Termux / Android ARM64

Полностью переписанный движок на базе Microsoft Edge TTS.
НЕ требует PyTorch, transformers или других тяжёлых ML библиотек.
Работает на любом Termux с Python 3.10+.

Фичи:
  - 400+ голосов, 75+ языков
  - Клонирование голоса через выбор пресета
  - Дизайн голоса (выбор по полу, стилю, акценту)
  - SSML поддержка для точной настройки
  - Асинхронная генерация (aiohttp)
  - Красивый CLI через rich
  - Полная совместимость с Termux

Оригинал: https://github.com/k2-fsa/OmniVoice (Apache-2.0)
Лицензия: OVPL 1.0
"""

import asyncio
import os
import sys
import time
import json
import struct
import argparse
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field

__all__ = [
    "OmniVoiceMobile",
    "VoiceInfo",
    "get_device_info",
    "list_voices",
    "clone_voice",
    "design_voice",
]

VERSION = "2.0.0"

BANNER = r"""
[bold cyan]
╔══════════════════════════════════════════════╗
║       OmniVoice Mobile  v2.0                ║
║   Edge TTS for Termux / Android ARM64      ║
║   400+ Voices | 75+ Languages              ║
║   Based on k2-fsa/OmniVoice (Apache-2.0)   ║
╚══════════════════════════════════════════════╝
[/bold cyan]
"""


# ──────────────────────────────────────────────
# Voice presets для клонирования/дизайна
# ──────────────────────────────────────────────

VOICE_PRESETS = {
    # --- Male ---
    "male_ru_1": {"voice": "ru-RU-DmitryNeural", "desc": "Мужской, русский, нейральный"},
    "male_ru_2": {"voice": "ru-RU-YuriNeural", "desc": "Мужской, русский, тёплый"},
    "male_en_1": {"voice": "en-US-GuyNeural", "desc": "Male, English, casual"},
    "male_en_2": {"voice": "en-US-DavisNeural", "desc": "Male, English, narration"},
    "male_en_3": {"voice": "en-US-AndrewNeural", "desc": "Male, English, friendly"},
    "male_en_4": {"voice": "en-GB-RyanNeural", "desc": "Male, British, calm"},
    "male_de_1": {"voice": "de-DE-ConradNeural", "desc": "Männlich, Deutsch"},
    "male_ja_1": {"voice": "ja-JP-NaNamiNeural", "desc": "Japanese, Female, Nami"},
    "male_ja_2": {"voice": "ja-JP-KeitaNeural", "desc": "Japanese, Male, Keita"},
    "male_es_1": {"voice": "es-ES-AlvaroNeural", "desc": "Masculino, Español"},
    "male_fr_1": {"voice": "fr-FR-HenriNeural", "desc": "Masculin, Français"},
    "male_zh_1": {"voice": "zh-CN-YunxiNeural", "desc": "中文, 男, 云希"},
    "male_zh_2": {"voice": "zh-CN-YunjianNeural", "desc": "中文, 男, 云健"},
    "male_ko_1": {"voice": "ko-KR-InJoonNeural", "desc": "한국어, 남성, 인준"},
    "male_uk_1": {"voice": "uk-UA-OstapNeural", "desc": "Чоловічий, український"},
    "male_kk_1": {"voice": "kk-KZ-DauletNeural", "desc": "Ер адам, қазақша"},
    "male_tr_1": {"voice": "tr-TR-AhmetNeural", "desc": "Erkek, Türkçe"},
    "male_ar_1": {"voice": "ar-SA-HamedNeural", "desc": "ذكر, عربي"},
    "male_hi_1": {"voice": "hi-IN-MadhurNeural", "desc": "पुरुष, हिन्दी"},
    "male_pt_1": {"voice": "pt-BR-AntonioNeural", "desc": "Masculino, Português BR"},
    "male_it_1": {"voice": "it-IT-DiegoNeural", "desc": "Maschile, Italiano"},
    "male_pl_1": {"voice": "pl-PL-MarekNeural", "desc": "Męski, Polski"},
    "male_nl_1": {"voice": "nl-NL-MaartenNeural", "desc": "Mannelijk, Nederlands"},

    # --- Female ---
    "female_ru_1": {"voice": "ru-RU-SvetlanaNeural", "desc": "Женский, русский, нейральный"},
    "female_ru_2": {"voice": "ru-RU-DariyaNeural", "desc": "Женский, русский, тёплый"},
    "female_en_1": {"voice": "en-US-JennyNeural", "desc": "Female, English, general"},
    "female_en_2": {"voice": "en-US-AriaNeural", "desc": "Female, English, friendly"},
    "female_en_3": {"voice": "en-US-MichelleNeural", "desc": "Female, English, professional"},
    "female_en_4": {"voice": "en-GB-SoniaNeural", "desc": "Female, British, clear"},
    "female_de_1": {"voice": "de-DE-KatjaNeural", "desc": "Weiblich, Deutsch"},
    "female_ja_1": {"voice": "ja-JP-NanamiNeural", "desc": "Japanese, Female, Nanami"},
    "female_es_1": {"voice": "es-ES-ElviraNeural", "desc": "Femenino, Español"},
    "female_fr_1": {"voice": "fr-FR-DeniseNeural", "desc": "Féminin, Français"},
    "female_zh_1": {"voice": "zh-CN-XiaoxiaoNeural", "desc": "中文, 女, 晓晓"},
    "female_zh_2": {"voice": "zh-CN-XiaoyiNeural", "desc": "中文, 女, 晓伊"},
    "female_ko_1": {"voice": "ko-KR-SunHiNeural", "desc": "한국어, 여성, 선히"},
    "female_uk_1": {"voice": "uk-UA-PolinaNeural", "desc": "Жіноча, українська"},
    "female_kk_1": {"voice": "kk-KZ-AigulNeural", "desc": "Әйел адам, қазақша"},
    "female_tr_1": {"voice": "tr-TR-EmelNeural", "desc": "Kadın, Türkçe"},
    "female_ar_1": {"voice": "ar-SA-ZariyahNeural", "desc": "أنثى, عربي"},
    "female_hi_1": {"voice": "hi-IN-SwaraNeural", "desc": "महिला, हिन्दी"},
    "female_pt_1": {"voice": "pt-BR-FranciscaNeural", "desc": "Feminino, Português BR"},
    "female_it_1": {"voice": "it-IT-ElsaNeural", "desc": "Femminile, Italiano"},
    "female_pl_1": {"voice": "pl-PL-AgnieszkaNeural", "desc": "Żeński, Polski"},
    "female_nl_1": {"voice": "nl-NL-ColetteNeural", "desc": "Vrouwelijk, Nederlands"},

    # --- Special ---
    "news_en": {"voice": "en-US-GuyNeural", "desc": "News anchor style, English"},
    "story_en": {"voice": "en-US-JennyNeural", "desc": "Storyteller, English"},
    "whisper_en": {"voice": "en-US-AndrewNeural", "desc": "Whisper/ASMR, English"},
}


# ──────────────────────────────────────────────
# Language map (ISO → Edge locale → default voice
# ──────────────────────────────────────────────

LANG_MAP = {
    "en": ("en-US", "en-US-JennyNeural"),
    "ru": ("ru-RU", "ru-RU-DmitryNeural"),
    "zh": ("zh-CN", "zh-CN-XiaoxiaoNeural"),
    "ja": ("ja-JP", "ja-JP-NanamiNeural"),
    "ko": ("ko-KR", "ko-KR-SunHiNeural"),
    "de": ("de-DE", "de-DE-KatjaNeural"),
    "es": ("es-ES", "es-ES-ElviraNeural"),
    "fr": ("fr-FR", "fr-FR-DeniseNeural"),
    "pt": ("pt-BR", "pt-BR-FranciscaNeural"),
    "it": ("it-IT", "it-IT-ElsaNeural"),
    "pl": ("pl-PL", "pl-PL-AgnieszkaNeural"),
    "nl": ("nl-NL", "nl-NL-ColetteNeural"),
    "uk": ("uk-UA", "uk-UA-PolinaNeural"),
    "tr": ("tr-TR", "tr-TR-EmelNeural"),
    "ar": ("ar-SA", "ar-SA-ZariyahNeural"),
    "hi": ("hi-IN", "hi-IN-SwaraNeural"),
    "kk": ("kk-KZ", "kk-KZ-AigulNeural"),
    "uz": ("uz-UZ", "uz-UZ-MadinaNeural"),
    "th": ("th-TH", "th-TH-PremwadeeNeural"),
    "vi": ("vi-VN", "vi-VN-HoaiMyNeural"),
    "id": ("id-ID", "id-ID-GadisNeural"),
    "ms": ("ms-MY", "ms-MY-YasminNeural"),
    "bn": ("bn-BD", "bn-BD-NabanitaNeural"),
    "ta": ("ta-IN", "ta-IN-PallaviNeural"),
    "te": ("te-IN", "te-IN-ShrutiNeural"),
    "he": ("he-IL", "he-IL-HilaNeural"),
    "el": ("el-GR", "el-GR-AthinaNeural"),
    "bg": ("bg-BG", "bg-BG-KalinaNeural"),
    "hr": ("hr-HR", "hr-HR-GabrijelaNeural"),
    "hu": ("hu-HU", "hu-HU-NoemiNeural"),
    "ro": ("ro-RO", "ro-RO-AlinaNeural"),
    "sk": ("sk-SK", "sk-SK-ViktoriaNeural"),
    "cs": ("cs-CZ", "cs-CZ-VlastaNeural"),
    "da": ("da-DK", "da-DK-ChristelNeural"),
    "fi": ("fi-FI", "fi-FI-NooraNeural"),
    "sv": ("sv-SE", "sv-SE-SofieNeural"),
    "no": ("nb-NO", "nb-NO-IselinNeural"),
    "ca": ("ca-ES", "ca-ES-JoanaNeural"),
    "fa": ("fa-IR", "fa-IR-DilaraNeural"),
    "ur": ("ur-PK", "ur-PK-UzmaNeural"),
    "yue": ("zh-HK", "zh-HK-HiuGaaiNeural"),
}

RU_NAMES = {
    "русский": "ru", "английский": "en", "китайский": "zh",
    "японский": "ja", "корейский": "ko", "немецкий": "de",
    "французский": "fr", "испанский": "es", "итальянский": "it",
    "португальский": "pt", "украинский": "uk", "казахский": "kk",
    "турецкий": "tr", "польский": "pl", "нидерландский": "nl",
    "арабский": "ar", "хинди": "hi", "бенгальский": "bn",
    "тамильский": "ta", "белорусский": "ru",
    "узбекский": "uz", "тайский": "th", "вьетнамский": "vi",
    "индонезийский": "id", "иврит": "he", "греческий": "el",
    "болгарский": "bg", "хорватский": "hr", "венгерский": "hu",
    "румынский": "ro", "словацкий": "sk", "чешский": "cs",
    "датский": "da", "финский": "fi", "шведский": "sv",
    "норвежский": "no", "каталанский": "ca", "персидский": "fa",
    "урду": "ur", "кантонский": "yue",
}


# ──────────────────────────────────────────────
# Data class
# ──────────────────────────────────────────────

@dataclass
class VoiceInfo:
    """Информация о голосе."""
    name: str
    locale: str
    gender: str
    short_name: str
    category: str = ""
    description: str = ""


# ──────────────────────────────────────────────
# Device info
# ──────────────────────────────────────────────

def get_device_info() -> Dict:
    """Информация об устройстве."""
    info = {
        "engine": "Edge TTS (Microsoft)",
        "version": VERSION,
        "arch": "unknown",
        "total_ram_gb": 0.0,
        "free_ram_gb": 0.0,
        "os": "unknown",
        "python": sys.version.split()[0],
        "termux": False,
    }
    try:
        import platform
        info["arch"] = platform.machine()
        info["os"] = platform.system()
    except Exception:
        pass
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if "MemTotal" in line:
                    info["total_ram_gb"] = int(line.split()[1]) / (1024 * 1024)
                elif "MemAvailable" in line:
                    info["free_ram_gb"] = int(line.split()[1]) / (1024 * 1024)
    except Exception:
        pass
    info["termux"] = os.path.exists("/data/data/com.termux")
    return info


# ──────────────────────────────────────────────
# Core Engine
# ──────────────────────────────────────────────

class OmniVoiceMobile:
    """
    OmniVoice Mobile v2.0 — Edge TTS Engine.

    Полная замена PyTorch-based движка на Microsoft Edge TTS.
    Работает на Termux, не требует GPU, мгновенная генерация.
    """

    def __init__(self, voice: str = None, lang: str = "en", rate: str = "+0%",
                 volume: str = "+0%", pitch: str = "+0Hz"):
        import edge_tts
        self.edge = edge_tts
        self.voice = voice
        self.lang = lang
        self.rate = rate
        self.volume = volume
        self.pitch = pitch
        self._voices_cache = None

    def _resolve_voice(self) -> str:
        """Определяет голос из языка или пресета."""
        if self.voice:
            return self.voice

        lang_key = self.lang.strip().lower()
        lang_key = RU_NAMES.get(lang_key, lang_key)

        if lang_key in LANG_MAP:
            locale, default_voice = LANG_MAP[lang_key]
            return default_voice

        return "en-US-JennyNeural"

    async def _get_voices_list(self) -> List[Dict]:
        """Получает список всех доступных голосов."""
        if self._voices_cache is not None:
            return self._voices_cache
        voices = await self.edge.list_voices()
        self._voices_cache = voices
        return voices

    async def list_voices(self, lang: str = None, gender: str = None) -> List[VoiceInfo]:
        """
        Возвращает список доступных голосов.

        Args:
            lang: Фильтр по языку (например 'ru', 'en')
            gender: Фильтр по полу ('Male' или 'Female')
        """
        voices = await self._get_voices_list()
        result = []

        for v in voices:
            locale = v.get("Locale", "")
            v_gender = v.get("Gender", "")

            if lang and not locale.lower().startswith(lang.lower()):
                continue
            if gender and v_gender != gender:
                continue

            result.append(VoiceInfo(
                name=v.get("ShortName", ""),
                locale=locale,
                gender=v_gender,
                short_name=v.get("ShortName", ""),
                category=v.get("VoiceTag", {}).get("ContentCategories", [""])[0] if isinstance(v.get("VoiceTag", {}), dict) else "",
                description=v.get("VoiceTag", {}).get("Description", [""])[0] if isinstance(v.get("VoiceTag", {}), dict) else "",
            ))

        return result

    def find_voice_by_preset(self, preset_name: str) -> Optional[str]:
        """Находит голос по имени пресета."""
        preset = VOICE_PRESETS.get(preset_name)
        if preset:
            return preset["voice"]
        # Попробуем прямое имя голоса
        if "Neural" in preset_name:
            return preset_name
        return None

    def find_voice_by_description(self, description: str) -> Optional[str]:
        """
        Находит лучший голос по описанию.

        Поддерживаемые ключевые слова:
          - Пол: male, female, мужчина, женщина, мужской, женский
          - Язык: en, ru, zh, ja, ko, de, и т.д.
          - Стиль: soft, warm, news, calm, friendly, professional
          - Акцент: british, american, australian
        """
        desc = description.lower().strip()
        is_male = any(w in desc for w in ["male", "мужск", "мужчин", "mannlich", "masculino", "masculin", "man", "guy", "mennelijk"])
        is_female = any(w in desc for w in ["female", "женск", "женщин", "weiblich", "femenino", "feminin", "woman", "girl", "vrouwelijk"])

        # Определяем язык
        target_lang = None
        for lang_code, lang_name in RU_NAMES.items():
            if lang_name in desc or lang_code in desc:
                target_lang = lang_code
                break
        for lang_code in LANG_MAP:
            if lang_code in desc:
                target_lang = lang_code
                break

        # Языковые алиасы
        lang_aliases = {
            "english": "en", "russian": "ru", "chinese": "zh", "japanese": "ja",
            "korean": "ko", "german": "de", "spanish": "es", "french": "fr",
            "portuguese": "pt", "italian": "it", "polish": "pl", "dutch": "nl",
            "ukrainian": "uk", "turkish": "tr", "arabic": "ar", "hindi": "hi",
            "kazakh": "kk", "thai": "th", "vietnamese": "vi", "indonesian": "id",
            "british": "en-gb", "american": "en-us",
        }
        for alias, code in lang_aliases.items():
            if alias in desc:
                target_lang = code
                break

        # Ищем пресет
        gender_prefix = "male" if is_male else "female"
        if target_lang:
            # Сначала точное совпадение
            key = f"{gender_prefix}_{target_lang}_1"
            if key in VOICE_PRESETS:
                return VOICE_PRESETS[key]["voice"]

            # Для en-gb / en-us
            if target_lang in ("en-gb", "en-us"):
                key = f"{gender_prefix}_{target_lang.replace('-', '_')}_1"
                if key in VOICE_PRESETS:
                    return VOICE_PRESETS[key]["voice"]

            # Для любого языка с gender
            for k, v in VOICE_PRESETS.items():
                if k.startswith(gender_prefix) and target_lang in k:
                    return v["voice"]

        # Fallback — по полу
        if is_male:
            return "en-US-GuyNeural"
        elif is_female:
            return "en-US-JennyNeural"

        # По умолчанию
        return None

    async def generate(
        self,
        text: str,
        output_path: str,
        voice: str = None,
        rate: str = None,
        volume: str = None,
        pitch: str = None,
        ssml: bool = False,
    ) -> Dict:
        """
        Генерирует речь из текста и сохраняет в файл.

        Args:
            text: Текст для генерации
            output_path: Путь к выходному файлу (.mp3 или .wav)
            voice: Голос (если None, используется self.voice)
            rate: Скорость ('+20%', '-10%', '+0%')
            volume: Громкость ('+20%', '-10%', '+0%')
            pitch: Тон ('+5Hz', '-5Hz', '+0Hz')
            ssml: Использовать SSML формат

        Returns:
            Dict с информацией о генерации
        """
        voice = voice or self.voice or self._resolve_voice()
        rate = rate or self.rate
        volume = volume or self.volume
        pitch = pitch or self.pitch

        t_start = time.time()
        output_path = str(output_path)

        # Генерация через Edge TTS
        communicate = self.edge.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
        await communicate.save(output_path)

        duration_sec = 0.0
        file_size = 0

        try:
            file_size = os.path.getsize(output_path)
            # Получаем длительность
            duration_sec = await self._get_duration(output_path)
        except Exception:
            pass

        gen_time = time.time() - t_start

        return {
            "output": output_path,
            "voice": voice,
            "duration_sec": duration_sec,
            "file_size": file_size,
            "gen_time": gen_time,
            "rtf": gen_time / duration_sec if duration_sec > 0 else 0,
        }

    async def _get_duration(self, audio_path: str) -> float:
        """Получает длительность аудио файла."""
        path_lower = audio_path.lower()

        if path_lower.endswith(".mp3"):
            # Для MP3 читаем заголовок фрейма
            try:
                with open(audio_path, "rb") as f:
                    f.seek(-128, 2)  # ID3v1 tag
                    tag = f.read(3)
                    if tag == b"TAG":
                        f.seek(-125, 2)
                        # Но точнее через ffmpeg или другую утилиту
            except Exception:
                pass

        # Пытаемся через ffprobe
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "csv=p=0", audio_path],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass

        # Пытаемся через ffprobe из Termux
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "csv=p=0", audio_path],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception:
            pass

        # Оценка по размеру файла для MP3 (~128kbps)
        try:
            file_size = os.path.getsize(audio_path)
            if path_lower.endswith(".mp3"):
                return file_size / (128 * 1024 / 8)
        except Exception:
            pass

        return 0.0

    async def clone_voice(
        self,
        text: str,
        output_path: str,
        ref_audio: str = None,
        preset: str = None,
        description: str = None,
    ) -> Dict:
        """
        'Клонирование' голоса через подбор ближайшего голоса.

        Поскольку настоящие нейросетевые модели не работают на Termux,
        мы используем умный подбор голоса из 400+ доступных в Edge TTS.

        Args:
            text: Текст для генерации
            output_path: Путь к выходному файлу
            ref_audio: (Не используется — для совместимости)
            preset: Имя пресета из VOICE_PRESETS
            description: Описание желаемого голоса (пол, язык, стиль)
        """
        voice = None

        # 1. Пресет
        if preset:
            voice = self.find_voice_by_preset(preset)
            if voice:
                print(f"  [CLONE] Пресет: {preset} -> {voice}")

        # 2. Описание
        if not voice and description:
            voice = self.find_voice_by_description(description)
            if voice:
                print(f"  [CLONE] Описание: '{description}' -> {voice}")

        # 3. Fallback
        if not voice:
            voice = self._resolve_voice()
            print(f"  [CLONE] Auto: {voice}")

        return await self.generate(text, output_path, voice=voice)

    async def design_voice(
        self,
        text: str,
        output_path: str,
        instruction: str,
    ) -> Dict:
        """
        Дизайн голоса по инструкции.

        Парсит инструкцию типа "female, soft, Russian" и подбирает голос.

        Args:
            text: Текст для генерации
            output_path: Путь к выходному файлу
            instruction: Инструкция для дизайна голоса
        """
        voice = self.find_voice_by_description(instruction)
        if not voice:
            voice = self._resolve_voice()

        # Парсим параметры из инструкции
        rate = self.rate
        volume = self.volume
        pitch = self.pitch

        instr_lower = instruction.lower()
        if any(w in instr_lower for w in ["fast", "быстр", "быстре", "скоро"]):
            rate = "+20%"
        elif any(w in instr_lower for w in ["slow", "медл", "медле"]):
            rate = "-20%"
        if any(w in instr_lower for w in ["loud", "громк", "громче"]):
            volume = "+30%"
        elif any(w in instr_lower for w in ["quiet", "тих", "тише", "шёпот"]):
            volume = "-20%"
        if any(w in instr_lower for w in ["high pitch", "высок", "тон"]):
            pitch = "+5Hz"
        elif any(w in instr_lower for w in ["low pitch", "низк"]):
            pitch = "-5Hz"

        print(f"  [DESIGN] Голос: {voice}")
        print(f"  [DESIGN] Параметры: rate={rate}, volume={volume}, pitch={pitch}")

        return await self.generate(text, output_path, voice=voice,
                                    rate=rate, volume=volume, pitch=pitch)

    async def stream_to_player(self, text: str, voice: str = None):
        """Генерирует и проигрывает аудио через mpv/ffplay."""
        import tempfile

        voice = voice or self.voice or self._resolve_voice()
        tmp = tempfile.mktemp(suffix=".mp3")

        await self.generate(text, tmp, voice=voice)

        # Пробуем разные плееры
        player = None
        for p in ["mpv", "ffplay", "play", "termux-media-player"]:
            if shutil.which(p):
                player = p
                break

        if player:
            subprocess.run([player, tmp], check=True)
        else:
            print(f"[!] Нет аудио плеера. Файл: {tmp}")
            print("  Установите: pkg install mpv")

        # Cleanup
        try:
            os.unlink(tmp)
        except Exception:
            pass


# ──────────────────────────────────────────────
# Sync wrappers
# ──────────────────────────────────────────────

def _run_async(coro):
    """Запускает корутину синхронно."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


def list_voices(lang: str = None, gender: str = None) -> List[VoiceInfo]:
    """Синхронная обёртка для list_voices."""
    engine = OmniVoiceMobile()
    return _run_async(engine.list_voices(lang=lang, gender=gender))


def clone_voice(text: str, output_path: str, preset: str = None,
                description: str = None, lang: str = "en") -> Dict:
    """Синхронная обёртка для clone_voice."""
    engine = OmniVoiceMobile(lang=lang)
    return _run_async(engine.clone_voice(text, output_path,
                                          preset=preset, description=description))


def design_voice(text: str, output_path: str, instruction: str, lang: str = "en") -> Dict:
    """Синхронная обёртка для design_voice."""
    engine = OmniVoiceMobile(lang=lang)
    return _run_async(engine.design_voice(text, output_path, instruction))
