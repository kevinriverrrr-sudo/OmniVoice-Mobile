"""
Карта языков OmniVoice.
Поддержка 600+ языков — здесь наиболее используемые.
Полная карта доступна в оригинальном репозитории.
"""

# Код ISO 639-1/3 → ID для модели
LANG_IDS = {
    # Основные языки
    "en": 0, "zh": 1, "de": 2, "es": 3, "ru": 4, "ko": 5, "fr": 6,
    "ja": 7, "pt": 8, "tr": 9, "pl": 10, "nl": 11, "uk": 12,
    "it": 13, "ar": 14, "sv": 15, "cs": 16, "vi": 17, "th": 18,
    "id": 19, "hi": 20, "fi": 21, "he": 22, "el": 23, "ms": 24,
    "no": 25, "da": 26, "hu": 27, "ro": 28, "bn": 29, "sk": 30,
    "tl": 31, "fa": 32, "bg": 33, "hr": 34, "ca": 35, "ur": 36,
    "ta": 37, "te": 38, "mr": 39, "ml": 40, "pa": 41, "gu": 42,
    "kn": 43, "si": 44, "km": 45, "my": 46, "ne": 47, "am": 48,
    "yo": 49, "ig": 50, "ha": 51, "sw": 52, "zu": 53, "xh": 54,
    "af": 55, "eu": 56, "ka": 57, "hy": 58, "is": 59, "sq": 60,
    "et": 61, "lv": 62, "lt": 63, "sl": 64, "tt": 65, "uz": 66,
    "kk": 67, "ky": 68, "az": 69, "tg": 70, "mn": 71, "ku": 72,
    "ps": 73, "ku": 74, "sd": 75, "sa": 76, "ne": 77, "as": 78,
    "or": 79, "mni": 80, "doi": 81, "kok": 82, "mai": 83,
    # Китайские диалекты
    "yue": 100, "cmn": 101, "wuu": 102, "nan": 103, "hak": 104,
    "gan": 105, "cpx": 106, "cjy": 107, "mnp": 108,
    # Español variantes
    "es-419": 200, "es-ES": 201, "es-MX": 202,
    # English variants
    "en-GB": 300, "en-US": 301, "en-AU": 302, "en-IN": 303,
    # French variants
    "fr-FR": 400, "fr-CA": 401,
    # Portuguese variants
    "pt-BR": 500, "pt-PT": 501,
}

# Обратная карта
LANG_NAMES = {v: k for k, v in LANG_IDS.items()}


def get_lang_id(lang_code: str) -> int:
    """Получить числовой ID языка."""
    return LANG_IDS.get(lang_code.lower(), 0)


def get_lang_name(lang_id: int) -> str:
    """Получить код языка по ID."""
    return LANG_NAMES.get(lang_id, "en")


def normalize_lang(lang: str) -> str:
    """Нормализует код языка."""
    lang = lang.strip().lower()
    # Заменяем русские названия
    ru_map = {
        "русский": "ru", "английский": "en", "китайский": "zh",
        "японский": "ja", "корейский": "ko", "немецкий": "de",
        "французский": "fr", "испанский": "es", "итальянский": "it",
        "португальский": "pt", "украинский": "uk", "казахский": "kk",
        "турецкий": "tr", "польский": "pl", "нидерландский": "nl",
        "арабский": "ar", "хинди": "hi", "бенгальский": "bn",
        "тамильский": "ta", "телугу": "te", "марафи": "mr",
    }
    if lang in ru_map:
        return ru_map[lang]
    return lang
