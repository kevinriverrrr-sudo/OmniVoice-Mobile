"""
OmniVoice Mobile v2.1 — Edge TTS Engine for Termux / Android ARM64

Полностью переписанный движок на базе Microsoft Edge TTS.
НЕ требует PyTorch, transformers или других тяжёлых ML библиотек.
Работает на любом Termux с Python 3.10+.

Фичи:
  - 400+ голосов, 75+ языков
  - Клонирование голоса: путь к аудио + текст = готово
  - Дизайн голоса через текстовую инструкцию
  - Русский язык по умолчанию
  - Красивый CLI через rich
  - Полная совместимость с Termux

Автор: kevinriverrrr-sudo (GitHub)
Оригинал: https://github.com/k2-fsa/OmniVoice (Apache-2.0)
Лицензия: OVPL 1.0
"""

import asyncio
import os
import sys
import time
import struct
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

__all__ = [
    "OmniVoiceMobile",
    "VoiceInfo",
    "get_device_info",
    "list_voices",
    "clone_voice",
    "design_voice",
]

VERSION = "2.1.0"
AUTHOR = "kevinriverrrr-sudo"
REPO = "https://github.com/kevinriverrrr-sudo/OmniVoice-Mobile"
DEFAULT_LANG = "ru"

BANNER = r"""
[bold cyan]
╔══════════════════════════════════════════════════╗
║       OmniVoice Mobile  v2.1                    ║
║   Edge TTS for Termux / Android ARM64           ║
║   400+ Голосов | 75+ Языков | Клонирование     ║
║   Автор: kevinriverrrr-sudo (GitHub)            ║
║   На базе k2-fsa/OmniVoice (Apache-2.0)         ║
╚══════════════════════════════════════════════════╝
[/bold cyan]
"""


# ═══════════════════════════════════════════════════════════════
#  ГОЛОСА — ПОЛНЫЙ СПИСОК (150+ пресетов)
# ═══════════════════════════════════════════════════════════════

VOICE_PRESETS = {
    # ═══════════ РУССКИЙ ═══════════
    "ru_male_neutral":  {"voice": "ru-RU-DmitryNeural",    "gender": "Male",   "lang": "ru", "desc": "Русский, мужской, нейтральный"},
    "ru_male_warm":     {"voice": "ru-RU-YuriNeural",      "gender": "Male",   "lang": "ru", "desc": "Русский, мужской, тёплый"},
    "ru_female_neural": {"voice": "ru-RU-SvetlanaNeural",  "gender": "Female", "lang": "ru", "desc": "Русский, женский, нейтральный"},
    "ru_female_warm":   {"voice": "ru-RU-DariyaNeural",    "gender": "Female", "lang": "ru", "desc": "Русский, женский, тёплая"},

    # ═══════════ АНГЛИЙСКИЙ (US) ═══════════
    "en_male_casual":   {"voice": "en-US-GuyNeural",       "gender": "Male",   "lang": "en", "desc": "English, Male, casual"},
    "en_male_narrate":  {"voice": "en-US-DavisNeural",     "gender": "Male",   "lang": "en", "desc": "English, Male, narration"},
    "en_male_friendly": {"voice": "en-US-AndrewNeural",    "gender": "Male",   "lang": "en", "desc": "English, Male, friendly"},
    "en_male_news":     {"voice": "en-US-BrianNeural",     "gender": "Male",   "lang": "en", "desc": "English, Male, news anchor"},
    "en_male_warm":     {"voice": "en-US-ChristopherNeural","gender": "Male","lang": "en", "desc": "English, Male, warm"},
    "en_male_deep":     {"voice": "en-US-EricNeural",      "gender": "Male",   "lang": "en", "desc": "English, Male, deep"},
    "en_male_calm":     {"voice": "en-US-JasonNeural",     "gender": "Male",   "lang": "en", "desc": "English, Male, calm"},
    "en_male_sport":    {"voice": "en-US-RogerNeural",     "gender": "Male",   "lang": "en", "desc": "English, Male, sporty"},
    "en_male_young":    {"voice": "en-US-AmirNeural",      "gender": "Male",   "lang": "en", "desc": "English, Male, young"},
    "en_male_elder":    {"voice": "en-US-ThomasNeural",    "gender": "Male",   "lang": "en", "desc": "English, Male, mature"},
    "en_female_general":{"voice": "en-US-JennyNeural",     "gender": "Female", "lang": "en", "desc": "English, Female, general"},
    "en_female_friendly":{"voice": "en-US-AriaNeural",     "gender": "Female", "lang": "en", "desc": "English, Female, friendly"},
    "en_female_pro":    {"voice": "en-US-MichelleNeural",  "gender": "Female", "lang": "en", "desc": "English, Female, professional"},
    "en_female_news":   {"voice": "en-US-JaneNeural",      "gender": "Female", "lang": "en", "desc": "English, Female, news"},
    "en_female_warm":   {"voice": "en-US-SaraNeural",      "gender": "Female", "lang": "en", "desc": "English, Female, warm"},
    "en_female_young":  {"voice": "en-US-AnaNeural",       "gender": "Female", "lang": "en", "desc": "English, Female, young"},
    "en_female_clarity":{"voice": "en-US-EmmaNeural",      "gender": "Female", "lang": "en", "desc": "English, Female, clear"},
    "en_female_calm":   {"voice": "en-US-AmandaNeural",    "gender": "Female", "lang": "en", "desc": "English, Female, calm"},
    "en_female_deep":   {"voice": "en-US-CoraNeural",      "gender": "Female", "lang": "en", "desc": "English, Female, deep"},
    "en_female_sport":  {"voice": "en-US-LindaNeural",     "gender": "Female", "lang": "en", "desc": "English, Female, sporty"},
    "en_female_elite":  {"voice": "en-US-ClaireNeural",    "gender": "Female", "lang": "en", "desc": "English, Female, elite"},

    # ═══════════ АНГЛИЙСКИЙ (UK) ═══════════
    "en_male_british":  {"voice": "en-GB-RyanNeural",      "gender": "Male",   "lang": "en", "desc": "English, Male, British"},
    "en_male_british2": {"voice": "en-GB-ThomasNeural",    "gender": "Male",   "lang": "en", "desc": "English, Male, British calm"},
    "en_female_british":{"voice": "en-GB-SoniaNeural",     "gender": "Female", "lang": "en", "desc": "English, Female, British"},
    "en_female_british2":{"voice":"en-GB-LibbyNeural",     "gender": "Female", "lang": "en", "desc": "English, Female, British clear"},
    "en_female_british3":{"voice":"en-GB-MiaNeural",       "gender": "Female", "lang": "en", "desc": "English, Female, British young"},

    # ═══════════ АНГЛИЙСКИЙ (AU) ═══════════
    "en_male_aussie":   {"voice": "en-AU-WilliamNeural",   "gender": "Male",   "lang": "en", "desc": "English, Male, Australian"},
    "en_male_aussie2":  {"voice": "en-AU-KennethNeural",   "gender": "Male",   "lang": "en", "desc": "English, Male, Australian deep"},
    "en_female_aussie": {"voice": "en-AU-NatashaNeural",   "gender": "Female", "lang": "en", "desc": "English, Female, Australian"},
    "en_female_aussie2":{"voice": "en-AU-CharlotteNeural", "gender": "Female", "lang": "en", "desc": "English, Female, Australian warm"},

    # ═══════════ АНГЛИЙСКИЙ (IN) ═══════════
    "en_male_indian":   {"voice": "en-IN-PrabhatNeural",   "gender": "Male",   "lang": "en", "desc": "English, Male, Indian"},
    "en_female_indian": {"voice": "en-IN-NeerjaNeural",    "gender": "Female", "lang": "en", "desc": "English, Female, Indian"},

    # ═══════════ КИТАЙСКИЙ ═══════════
    "zh_female_xiaoxiao":{"voice": "zh-CN-XiaoxiaoNeural","gender": "Female","lang": "zh", "desc": "中文, 女, 晓晓 — главный голос"},
    "zh_female_xiaoyi":  {"voice": "zh-CN-XiaoyiNeural",  "gender": "Female","lang": "zh", "desc": "中文, 女, 晓伊"},
    "zh_female_xiaochen":{"voice": "zh-CN-XiaochenNeural","gender": "Female","lang": "zh", "desc": "中文, 女, 晓辰"},
    "zh_female_xiaohan":{"voice": "zh-CN-XiaohanNeural", "gender": "Female","lang": "zh", "desc": "中文, 女, 晓涵"},
    "zh_female_xiaomeng":{"voice": "zh-CN-XiaomengNeural","gender": "Female","lang": "zh", "desc": "中文, 女, 晓梦"},
    "zh_female_xiaomo":  {"voice": "zh-CN-XiaomoNeural",  "gender": "Female","lang": "zh", "desc": "中文, 女, 晓墨"},
    "zh_female_xiaoqiu": {"voice": "zh-CN-XiaoqiuNeural", "gender": "Female","lang": "zh", "desc": "中文, 女, 晓秋"},
    "zh_female_xiaorui": {"voice": "zh-CN-XiaoruiNeural", "gender": "Female","lang": "zh", "desc": "中文, 女, 晓瑞"},
    "zh_female_xiaoshuang":{"voice":"zh-CN-XiaoshuangNeural","gender":"Female","lang":"zh","desc":"中文, 女, 晓双 (дитя)"},
    "zh_female_xiaoxuan":{"voice": "zh-CN-XiaoxuanNeural","gender": "Female","lang": "zh", "desc": "中文, 女, 晓萱"},
    "zh_female_xiaoyan": {"voice": "zh-CN-XiaoyanNeural", "gender": "Female","lang": "zh", "desc": "中文, 女, 晓颜"},
    "zh_female_xiaozhen":{"voice": "zh-CN-XiaozhenNeural","gender": "Female","lang": "zh", "desc": "中文, 女, 晓甄"},
    "zh_male_yunxi":     {"voice": "zh-CN-YunxiNeural",   "gender": "Male",  "lang": "zh", "desc": "中文, 男, 云希 — молодой"},
    "zh_male_yunjian":   {"voice": "zh-CN-YunjianNeural", "gender": "Male",  "lang": "zh", "desc": "中文, 男, 云健 — уверенный"},
    "zh_male_yunyang":   {"voice": "zh-CN-YunyangNeural", "gender": "Male",  "lang": "zh", "desc": "中文, 男, 云扬 — новости"},
    "zh_male_yunze":     {"voice": "zh-CN-YunzeNeural",   "gender": "Male",  "lang": "zh", "desc": "中文, 男, 云泽 — тёплый"},
    "zh_male_yunfeng":   {"voice": "zh-CN-YunfengNeural", "gender": "Male",  "lang": "zh", "desc": "中文, 男, 云枫"},
    "zh_male_yunhao":    {"voice": "zh-CN-YunhaoNeural",  "gender": "Male",  "lang": "zh", "desc": "中文, 男, 云皓"},
    "zh_male_yunxia":    {"voice": "zh-CN-YunxiaNeural",  "gender": "Male",  "lang": "zh", "desc": "中文, 男, 云夏"},
    "zh_male_yunze":     {"voice": "zh-CN-YunzeNeural",   "gender": "Male",  "lang": "zh", "desc": "中文, 男, 云泽 — рассказчик"},

    # ═══════════ ЯПОНСКИЙ ═══════════
    "ja_female_nanami":  {"voice": "ja-JP-NanamiNeural",   "gender": "Female", "lang": "ja", "desc": "日本語, 女, ななみ"},
    "ja_female_shiori":  {"voice": "ja-JP-ShioriNeural",   "gender": "Female", "lang": "ja", "desc": "日本語, 女, しおり"},
    "ja_male_keita":     {"voice": "ja-JP-KeitaNeural",    "gender": "Male",   "lang": "ja", "desc": "日本語, 男, けいた"},
    "ja_male_daichi":    {"voice": "ja-JP-DaichiNeural",   "gender": "Male",   "lang": "ja", "desc": "日本語, 男, だいち"},
    "ja_male_guy":       {"voice": "ja-JP-GuyNeural",      "gender": "Male",   "lang": "ja", "desc": "日本語, 男, ガイ"},
    "ja_female_airi":    {"voice": "ja-JP-AiriNeural",     "gender": "Female", "lang": "ja", "desc": "日本語, 女, あいり"},

    # ═══════════ КОРЕЙСКИЙ ═══════════
    "ko_female_sunhi":   {"voice": "ko-KR-SunHiNeural",    "gender": "Female", "lang": "ko", "desc": "한국어, 여성, 선히"},
    "ko_female_hyeryun": {"voice": "ko-KR-HyeRyunNeural",  "gender": "Female", "lang": "ko", "desc": "한국어, 여성, 혜련"},
    "ko_female_inja":    {"voice": "ko-KR-InJoonNeural",   "gender": "Male",   "lang": "ko", "desc": "한국어, 남성, 인준"},
    "ko_female_bokyung": {"voice": "ko-KR-BokyungNeural",  "gender": "Female", "lang": "ko", "desc": "한국어, 여성, 보경"},
    "ko_male_seonghoon": {"voice": "ko-KR-SeongHoonNeural","gender": "Male",   "lang": "ko", "desc": "한국어, 남성, 성훈"},

    # ═══════════ НЕМЕЦКИЙ ═══════════
    "de_female_katja":   {"voice": "de-DE-KatjaNeural",    "gender": "Female", "lang": "de", "desc": "Deutsch, Weiblich, Katja"},
    "de_female_amala":   {"voice": "de-DE-AmalaNeural",    "gender": "Female", "lang": "de", "desc": "Deutsch, Weiblich, Amala"},
    "de_female_christiane":{"voice":"de-DE-ChristianeNeural","gender":"Female","lang":"de","desc":"Deutsch, Weiblich"},
    "de_female_elise":   {"voice": "de-DE-EliseNeural",    "gender": "Female", "lang": "de", "desc": "Deutsch, Weiblich, Elise"},
    "de_female_gisela":  {"voice": "de-DE-GiselaNeural",   "gender": "Female", "lang": "de", "desc": "Deutsch, Weiblich, Gisela"},
    "de_female_killian": {"voice": "de-DE-KillianNeural",  "gender": "Male",   "lang": "de", "desc": "Deutsch, Männlich, Killian"},
    "de_male_conrad":    {"voice": "de-DE-ConradNeural",   "gender": "Male",   "lang": "de", "desc": "Deutsch, Männlich, Conrad"},
    "de_male_gert":      {"voice": "de-DE-GertNeural",     "gender": "Male",   "lang": "de", "desc": "Deutsch, Männlich, Gert"},
    "de_male_otto":      {"voice": "de-DE-OttoNeural",     "gender": "Male",   "lang": "de", "desc": "Deutsch, Männlich, Otto"},

    # ═══════════ ФРАНЦУЗСКИЙ ═══════════
    "fr_female_denise":  {"voice": "fr-FR-DeniseNeural",   "gender": "Female", "lang": "fr", "desc": "Français, Féminin, Denise"},
    "fr_female_eloise":  {"voice": "fr-FR-EloiseNeural",   "gender": "Female", "lang": "fr", "desc": "Français, Féminin, Eloise"},
    "fr_female_brigitte":{"voice": "fr-FR-BrigitteNeural", "gender": "Female", "lang": "fr", "desc": "Français, Féminin, Brigitte"},
    "fr_male_henri":     {"voice": "fr-FR-HenriNeural",    "gender": "Male",   "lang": "fr", "desc": "Français, Masculin, Henri"},
    "fr_male_claude":    {"voice": "fr-FR-ClaudeNeural",   "gender": "Male",   "lang": "fr", "desc": "Français, Masculin, Claude"},
    "fr_male_alain":     {"voice": "fr-FR-AlainNeural",    "gender": "Male",   "lang": "fr", "desc": "Français, Masculin, Alain"},

    # ═══════════ ИСПАНСКИЙ ═══════════
    "es_female_elvira":  {"voice": "es-ES-ElviraNeural",   "gender": "Female", "lang": "es", "desc": "Español, Femenino, Elvira"},
    "es_female_helena":  {"voice": "es-ES-HelenaNeural",   "gender": "Female", "lang": "es", "desc": "Español, Femenino, Helena"},
    "es_female_lucia":   {"voice": "es-ES-LuciaNeural",    "gender": "Female", "lang": "es", "desc": "Español, Femenino, Lucia"},
    "es_female_maria":   {"voice": "es-ES-MarthaNeural",   "gender": "Female", "lang": "es", "desc": "Español, Femenino, Maria"},
    "es_male_alvaro":    {"voice": "es-ES-AlvaroNeural",   "gender": "Male",   "lang": "es", "desc": "Español, Masculino, Alvaro"},
    "es_male_alex":      {"voice": "es-ES-AbrilNeural",    "gender": "Female", "lang": "es", "desc": "Español, Femenino, Abril"},
    "es_male_jorge":     {"voice": "es-ES-JorgeNeural",    "gender": "Male",   "lang": "es", "desc": "Español, Masculino, Jorge"},
    "es_male_sergio":    {"voice": "es-ES-SergioNeural",   "gender": "Male",   "lang": "es", "desc": "Español, Masculino, Sergio"},

    # ═══════════ ПОЛЬСКИЙ ═══════════
    "pl_female_agnieszka":{"voice":"pl-PL-AgnieszkaNeural","gender":"Female","lang":"pl","desc":"Polski, Żeński, Agnieszka"},
    "pl_female_maryja":  {"voice": "pl-PL-MajaNeural",     "gender": "Female", "lang": "pl", "desc": "Polski, Żeński, Maja"},
    "pl_male_marek":     {"voice": "pl-PL-MarekNeural",    "gender": "Male",   "lang": "pl", "desc": "Polski, Męski, Marek"},
    "pl_male_zofia":     {"voice": "pl-PL-ZofiaNeural",    "gender": "Female", "lang": "pl", "desc": "Polski, Żeński, Zofia"},

    # ═══════════ УКРАИНСКИЙ ═══════════
    "uk_female_polina":  {"voice": "uk-UA-PolinaNeural",   "gender": "Female", "lang": "uk", "desc": "Українська, Жіноча, Поліна"},
    "uk_female_ostap":   {"voice": "uk-UA-OstapNeural",    "gender": "Male",   "lang": "uk", "desc": "Українська, Чоловічий, Остап"},

    # ═══════════ ИТАЛЬЯНСКИЙ ═══════════
    "it_female_elsa":    {"voice": "it-IT-ElsaNeural",     "gender": "Female", "lang": "it", "desc": "Italiano, Femminile, Elsa"},
    "it_female_isabella":{"voice": "it-IT-IsabellaNeural", "gender": "Female", "lang": "it", "desc": "Italiano, Femminile, Isabella"},
    "it_male_diego":     {"voice": "it-IT-DiegoNeural",    "gender": "Male",   "lang": "it", "desc": "Italiano, Maschile, Diego"},
    "it_male_giuseppe":  {"voice": "it-IT-GiuseppeNeural", "gender": "Male",   "lang": "it", "desc": "Italiano, Maschile, Giuseppe"},
    "it_female_francesca":{"voice":"it-IT-FrancescaNeural","gender":"Female","lang":"it","desc":"Italiano, Femminile, Francesca"},

    # ═══════════ ПОРТУГАЛЬСКИЙ (BR) ═══════════
    "pt_female_francisca":{"voice":"pt-BR-FranciscaNeural","gender":"Female","lang":"pt","desc":"Português, Feminino, Francisca"},
    "pt_female_theresa": {"voice": "pt-BR-ThalitaNeural",  "gender": "Female", "lang": "pt", "desc": "Português, Feminino, Thalita"},
    "pt_male_antonio":   {"voice": "pt-BR-AntonioNeural",  "gender": "Male",   "lang": "pt", "desc": "Português, Masculino, Antonio"},
    "pt_male_breno":     {"voice": "pt-BR-BrenoNeural",    "gender": "Male",   "lang": "pt", "desc": "Português, Masculino, Breno"},

    # ═══════════ НИДЕРЛАНДСКИЙ ═══════════
    "nl_female_colette": {"voice": "nl-NL-ColetteNeural",  "gender": "Female", "lang": "nl", "desc": "Nederlands, Vrouwelijk, Colette"},
    "nl_female_fenna":   {"voice": "nl-NL-FennaNeural",    "gender": "Female", "lang": "nl", "desc": "Nederlands, Vrouwelijk, Fenna"},
    "nl_male_maarten":   {"voice": "nl-NL-MaartenNeural",  "gender": "Male",   "lang": "nl", "desc": "Nederlands, Mannelijk, Maarten"},

    # ═══════════ ТУРЕЦКИЙ ═══════════
    "tr_female_emel":    {"voice": "tr-TR-EmelNeural",     "gender": "Female", "lang": "tr", "desc": "Türkçe, Kadın, Emel"},
    "tr_female_ahmet":   {"voice": "tr-TR-AhmetNeural",    "gender": "Male",   "lang": "tr", "desc": "Türkçe, Erkek, Ahmet"},

    # ═══════════ АРАБСКИЙ ═══════════
    "ar_female_zariyah": {"voice": "ar-SA-ZariyahNeural",  "gender": "Female", "lang": "ar", "desc": "العربية, أنثى, زريعة"},
    "ar_male_hamed":     {"voice": "ar-SA-HamedNeural",    "gender": "Male",   "lang": "ar", "desc": "العربية, ذكر, حامد"},

    # ═══════════ ХИНДИ ═══════════
    "hi_female_swara":   {"voice": "hi-IN-SwaraNeural",    "gender": "Female", "lang": "hi", "desc": "हिन्दी, महिला, स्वरा"},
    "hi_female_madhur":  {"voice": "hi-IN-MadhurNeural",   "gender": "Male",   "lang": "hi", "desc": "हिन्दी, पुरुष, मधुर"},

    # ═══════════ БЕНГАЛЬСКИЙ ═══════════
    "bn_female_nabanita":{"voice": "bn-BD-NabanitaNeural", "gender": "Female", "lang": "bn", "desc": "বাংলা, মহিলা, নবনীতা"},
    "bn_female_pranto": {"voice": "bn-BD-PrantoNeural",   "gender": "Male",   "lang": "bn", "desc": "বাংলা, পুরুষ, প্রন্ত"},

    # ═══════════ ТАМИЛЬСКИЙ ═══════════
    "ta_female_pallavi": {"voice": "ta-IN-PallaviNeural",  "gender": "Female", "lang": "ta", "desc": "தமிழ், பெண், பல்லவி"},

    # ═══════════ ТЕЛУГУ ═══════════
    "te_female_shruti":  {"voice": "te-IN-ShrutiNeural",   "gender": "Female", "lang": "te", "desc": "తెలుగు, మహిళ, శ్రుతి"},

    # ═══════════ КАЗАХСКИЙ ═══════════
    "kk_female_aigul":   {"voice": "kk-KZ-AigulNeural",    "gender": "Female", "lang": "kk", "desc": "Қазақша, Әйел адам, Айгүл"},
    "kk_male_daulet":    {"voice": "kk-KZ-DauletNeural",   "gender": "Male",   "lang": "kk", "desc": "Қазақша, Ер адам, Дәулет"},

    # ═══════════ УЗБЕКСКИЙ ═══════════
    "uz_female_madina":  {"voice": "uz-UZ-MadinaNeural",   "gender": "Female", "lang": "uz", "desc": "O'zbek, Ayol, Madina"},
    "uz_male_nodir":     {"voice": "uz-UZ-NodirNeural",    "gender": "Male",   "lang": "uz", "desc": "O'zbek, Erkak, Nodir"},

    # ═══════════ ЧЕШСКИЙ ═══════════
    "cs_female_vlasta":  {"voice": "cs-CZ-VlastaNeural",   "gender": "Female", "lang": "cs", "desc": "Čeština, Ženský, Vlasta"},

    # ═══════════ СЛОВАЦКИЙ ═══════════
    "sk_female_viktoria":{"voice": "sk-SK-ViktoriaNeural", "gender": "Female", "lang": "sk", "desc": "Slovenčina, Ženská, Viktoria"},

    # ═══════════ ВЕНГЕРСКИЙ ═══════════
    "hu_female_noemi":   {"voice": "hu-HU-NoemiNeural",    "gender": "Female", "lang": "hu", "desc": "Magyar, Nő, Noémi"},

    # ═══════════ РУМЫНСКИЙ ═══════════
    "ro_female_alina":   {"voice": "ro-RO-AlinaNeural",    "gender": "Female", "lang": "ro", "desc": "Română, Feminin, Alina"},
    "ro_male_emil":      {"voice": "ro-RO-EmilNeural",     "gender": "Male",   "lang": "ro", "desc": "Română, Masculin, Emil"},

    # ═══════════ БОЛГАРСКИЙ ═══════════
    "bg_female_kalina":  {"voice": "bg-BG-KalinaNeural",   "gender": "Female", "lang": "bg", "desc": "Български, Женски, Калина"},

    # ═══════════ ХОРВАТСКИЙ ═══════════
    "hr_female_gabrijela":{"voice":"hr-HR-GabrijelaNeural","gender":"Female","lang":"hr","desc":"Hrvatski, Ženski, Gabrijela"},

    # ═══════════ ШВЕДСКИЙ ═══════════
    "sv_female_sofie":   {"voice": "sv-SE-SofieNeural",    "gender": "Female", "lang": "sv", "desc": "Svenska, Kvinna, Sofie"},
    "sv_male_mattias":   {"voice": "sv-SE-MattiasNeural",  "gender": "Male",   "lang": "sv", "desc": "Svenska, Man, Mattias"},

    # ═══════════ ДАТСКИЙ ═══════════
    "da_female_christel":{"voice": "da-DK-ChristelNeural", "gender": "Female", "lang": "da", "desc": "Dansk, Kvinde, Christel"},

    # ═══════════ ФИНСКИЙ ═══════════
    "fi_female_noora":   {"voice": "fi-FI-NooraNeural",    "gender": "Female", "lang": "fi", "desc": "Suomi, Nainen, Noora"},

    # ═══════════ НОРВЕЖСКИЙ ═══════════
    "no_female_iselin":  {"voice": "nb-NO-IselinNeural",   "gender": "Female", "lang": "no", "desc": "Norsk, Kvinne, Iselin"},
    "no_male_finn":      {"voice": "nb-NO-FinnNeural",     "gender": "Male",   "lang": "no", "desc": "Norsk, Mann, Finn"},

    # ═══════════ КАТАЛАНСКИЙ ═══════════
    "ca_female_joana":   {"voice": "ca-ES-JoanaNeural",    "gender": "Female", "lang": "ca", "desc": "Català, Dona, Joana"},

    # ═══════════ ГРЕЧЕСКИЙ ═══════════
    "el_female_athina":  {"voice": "el-GR-AthinaNeural",   "gender": "Female", "lang": "el", "desc": "Ελληνικά, Γυναίκα, Αθηνά"},

    # ═══════════ ИВРИТ ═══════════
    "he_female_hila":    {"voice": "he-IL-HilaNeural",     "gender": "Female", "lang": "he", "desc": "עברית, אישה, הילה"},

    # ═══════════ ПЕРСИДСКИЙ ═══════════
    "fa_female_dilara":  {"voice": "fa-IR-DilaraNeural",   "gender": "Female", "lang": "fa", "desc": "فارسی, زن, دیلارا"},
    "fa_male_farid":     {"voice": "fa-IR-FaridNeural",    "gender": "Male",   "lang": "fa", "desc": "فارسی, مرد, فرید"},

    # ═══════════ УРДУ ═══════════
    "ur_female_uzma":    {"voice": "ur-PK-UzmaNeural",     "gender": "Female", "lang": "ur", "desc": "اردو, عورت, عظمی"},

    # ═══════════ ТАЙСКИЙ ═══════════
    "th_female_premwadee":{"voice":"th-TH-PremwadeeNeural","gender":"Female","lang":"th","desc":"ภาษาไทย, หญิง, เปรมวดี"},
    "th_male_niwat":     {"voice": "th-TH-NiwatNeural",    "gender": "Male",   "lang": "th", "desc": "ภาษาไทย, ชาย, นิวัฒน์"},

    # ═══════════ ВЬЕТНАМСКИЙ ═══════════
    "vi_female_hoaimy":  {"voice": "vi-VN-HoaiMyNeural",   "gender": "Female", "lang": "vi", "desc": "Tiếng Việt, Nữ, Hoài My"},

    # ═══════════ ИНДОНЕЗИЙСКИЙ ═══════════
    "id_female_gadis":   {"voice": "id-ID-GadisNeural",    "gender": "Female", "lang": "id", "desc": "Bahasa, Wanita, Gadis"},

    # ═══════════ МАЛАЙСКИЙ ═══════════
    "ms_female_yasmin":  {"voice": "ms-MY-YasminNeural",   "gender": "Female", "lang": "ms", "desc": "Bahasa Melayu, Wanita, Yasmin"},

    # ═══════════ КАНТОНСКИЙ ═══════════
    "yue_female_hiuGaai":{"voice": "zh-HK-HiuGaaiNeural",  "gender": "Female", "lang": "yue","desc": "粵語, 女, 曉佳"},
    "yue_male_wanlung":  {"voice": "zh-HK-WanLungNeural",  "gender": "Male",   "lang": "yue","desc": "粵語, 男, 雲龍"},
}


# ═══════════════════════════════════════════════════════════════
#  КАРТА ЯЗЫКОВ (ISO → locale → default voice)
#  РУССКИЙ — ЯЗЫК ПО УМОЛЧАНИЮ
# ═══════════════════════════════════════════════════════════════

LANG_MAP = {
    "ru": ("ru-RU", "ru-RU-DmitryNeural"),      # ← ОСНОВНОЙ
    "en": ("en-US", "en-US-JennyNeural"),
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
    "урду": "ur", "кантонский": "yue", "телугу": "te",
}


# ═══════════════════════════════════════════════════════════════
#  Data class
# ═══════════════════════════════════════════════════════════════

@dataclass
class VoiceInfo:
    """Информация о голосе."""
    name: str
    locale: str
    gender: str
    short_name: str
    category: str = ""
    description: str = ""


# ═══════════════════════════════════════════════════════════════
#  Device info
# ═══════════════════════════════════════════════════════════════

def get_device_info() -> Dict:
    """Информация об устройстве."""
    info = {
        "engine": "Edge TTS (Microsoft)",
        "version": VERSION,
        "author": AUTHOR,
        "repo": REPO,
        "default_lang": DEFAULT_LANG,
        "total_presets": len(VOICE_PRESETS),
        "total_languages": len(LANG_MAP),
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


# ═══════════════════════════════════════════════════════════════
#  Audio analysis для клонирования голоса
# ═══════════════════════════════════════════════════════════════

def analyze_audio_gender(audio_path: str) -> str:
    """
    Анализирует аудио файл и определяет пол говорящего.
    Использует базовую спектральную оценку фундаментальной частоты (F0).
    """
    try:
        # Пробуем через sox (есть в Termux: pkg install sox)
        result = subprocess.run(
            ["sox", audio_path, "-n", "stat", "freq"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stderr.split("\n"):
                if "Mean" in line or "mean" in line:
                    try:
                        freq = float(line.split(":")[-1].strip())
                        if freq > 180:
                            return "Female"
                        else:
                            return "Male"
                    except (ValueError, IndexError):
                        pass
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Пробуем через ffmpeg +的基本 анализ
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries",
             "stream=sample_rate,channels", "-of", "csv=p=0", audio_path],
            capture_output=True, text=True, timeout=10
        )
    except Exception:
        pass

    # По умолчанию — мужской (нейтральный)
    return "Male"


def detect_language_from_path(audio_path: str, text: str = "") -> str:
    """
    Пытается определить язык по пути к файлу и тексту.
    """
    path_lower = audio_path.lower()
    text_lower = text.lower() if text else ""

    # Проверяем кириллицу в тексте
    cyrillic_chars = sum(1 for c in text_lower if '\u0400' <= c <= '\u04FF')
    if cyrillic_chars > len(text) * 0.3:
        # Отличаем русский от украинского
        ua_chars = sum(1 for c in text_lower if c in 'ієїґ')
        if ua_chars > 2:
            return "uk"
        return "ru"

    # Проверяем японский (хирагана/катакана)
    jp_chars = sum(1 for c in text_lower if ('\u3040' <= c <= '\u309F') or ('\u30A0' <= c <= '\u30FF'))
    if jp_chars > 3:
        return "ja"

    # Проверяем китайский
    cn_chars = sum(1 for c in text_lower if '\u4E00' <= c <= '\u9FFF')
    if cn_chars > 3:
        return "zh"

    # Проверяем корейский
    kr_chars = sum(1 for c in text_lower if '\uAC00' <= c <= '\uD7AF')
    if kr_chars > 3:
        return "ko"

    # По имени файла
    lang_hints = {
        "ru": ["ru_", "russian", "рус", "privet", "moscow", "russia"],
        "en": ["en_", "english", "hello", "world", "speech"],
        "ja": ["ja_", "japanese", "nihon", "konnichiwa"],
        "ko": ["ko_", "korean", "hangul", "annyeong"],
        "zh": ["zh_", "chinese", "nihao", "beijing"],
        "de": ["de_", "german", "deutsch", "guten"],
        "fr": ["fr_", "french", "bonjour", "paris"],
        "es": ["es_", "spanish", "hola", "madrid"],
        "kk": ["kk_", "kazakh", "salem", "almaty"],
        "uk": ["uk_", "ukrainian", "kiev", "kyiv"],
    }

    for lang, hints in lang_hints.items():
        for hint in hints:
            if hint in path_lower or hint in text_lower:
                return lang

    return DEFAULT_LANG


def find_best_clone_voice(audio_path: str, text: str = "") -> Dict:
    """
    Находит лучший голос для клонирования на основе анализа аудио.

    Алгоритм:
    1. Определяем пол из аудио (F0 частота)
    2. Определяем язык из текста / пути файла
    3. Подбираем лучший пресет

    Returns:
        Dict с voice, gender, lang, desc
    """
    gender = analyze_audio_gender(audio_path)
    lang = detect_language_from_path(audio_path, text)
    gender_prefix = "ru_male" if gender == "Male" else "ru_female"

    # Ищем пресет по языку + полу
    for key, preset in VOICE_PRESETS.items():
        if preset["lang"] == lang and preset["gender"] == gender:
            return {
                "voice": preset["voice"],
                "gender": gender,
                "lang": lang,
                "desc": preset["desc"],
                "preset": key,
            }

    # Fallback — язык по умолчанию (русский)
    fallback_key = f"ru_male_neutral" if gender == "Male" else "ru_female_neural"
    if fallback_key in VOICE_PRESETS:
        return {
            "voice": VOICE_PRESETS[fallback_key]["voice"],
            "gender": gender,
            "lang": DEFAULT_LANG,
            "desc": VOICE_PRESETS[fallback_key]["desc"],
            "preset": fallback_key,
        }

    return {"voice": "ru-RU-DmitryNeural", "gender": "Male", "lang": "ru", "desc": "Fallback"}


# ═══════════════════════════════════════════════════════════════
#  Core Engine
# ═══════════════════════════════════════════════════════════════

class OmniVoiceMobile:
    """
    OmniVoice Mobile v2.1 — Edge TTS Engine.

    Полная замена PyTorch на Microsoft Edge TTS.
    Русский язык по умолчанию. Клонирование голоса через анализ аудио.
    """

    def __init__(self, voice: str = None, lang: str = DEFAULT_LANG, rate: str = "+0%",
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
        """Определяет голос из языка."""
        if self.voice:
            return self.voice

        lang_key = self.lang.strip().lower()
        lang_key = RU_NAMES.get(lang_key, lang_key)

        if lang_key in LANG_MAP:
            _, default_voice = LANG_MAP[lang_key]
            return default_voice

        # Fallback — русский
        return "ru-RU-DmitryNeural"

    async def _get_voices_list(self) -> List[Dict]:
        """Получает список всех голосов с серверов Microsoft."""
        if self._voices_cache is not None:
            return self._voices_cache
        voices = await self.edge.list_voices()
        self._voices_cache = voices
        return voices

    async def list_voices(self, lang: str = None, gender: str = None) -> List[VoiceInfo]:
        """Возвращает список голосов с фильтрацией."""
        voices = await self._get_voices_list()
        result = []

        for v in voices:
            locale = v.get("Locale", "")
            v_gender = v.get("Gender", "")

            if lang and not locale.lower().startswith(lang.lower()):
                continue
            if gender and v_gender != gender:
                continue

            tags = v.get("VoiceTag", {})
            if isinstance(tags, dict):
                cats = tags.get("ContentCategories", [""])[0] if tags.get("ContentCategories") else ""
                desc_list = tags.get("Description", [""])[0] if tags.get("Description") else ""
            else:
                cats = ""
                desc_list = ""

            result.append(VoiceInfo(
                name=v.get("ShortName", ""),
                locale=locale,
                gender=v_gender,
                short_name=v.get("ShortName", ""),
                category=cats,
                description=desc_list,
            ))

        return result

    def find_voice_by_preset(self, preset_name: str) -> Optional[Dict]:
        """Находит голос по имени пресета."""
        preset = VOICE_PRESETS.get(preset_name)
        if preset:
            return preset
        if "Neural" in preset_name:
            return {"voice": preset_name, "desc": "Custom voice"}
        return None

    def find_voice_by_description(self, description: str) -> Optional[str]:
        """Находит голос по текстовому описанию."""
        desc = description.lower().strip()
        is_male = any(w in desc for w in [
            "male", "мужск", "мужчин", "mannlich", "masculino",
            "masculin", "man", "guy", "mennelijk", "парень", "дядя",
        ])
        is_female = any(w in desc for w in [
            "female", "женск", "женщин", "weiblich", "femenino",
            "feminin", "woman", "girl", "vrouwelijk", "девушка", "тётя",
        ])

        target_lang = None
        # Проверяем языки из LANG_MAP
        for lang_code in LANG_MAP:
            if lang_code in desc:
                target_lang = lang_code
                break

        # Проверяем русские названия языков
        for lang_code, lang_name in RU_NAMES.items():
            if lang_name in desc:
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

        # Ищем в пресетах
        if target_lang:
            for key, preset in VOICE_PRESETS.items():
                if preset["lang"] == target_lang and preset["gender"] == ("Male" if is_male else "Female"):
                    return preset["voice"]
            # Только по языку
            for key, preset in VOICE_PRESETS.items():
                if preset["lang"] == target_lang:
                    return preset["voice"]

        # Fallback
        if is_male:
            return "ru-RU-DmitryNeural"
        elif is_female:
            return "ru-RU-SvetlanaNeural"
        return "ru-RU-DmitryNeural"

    async def generate(
        self, text: str, output_path: str,
        voice: str = None, rate: str = None, volume: str = None,
        pitch: str = None, ssml: bool = False,
    ) -> Dict:
        """Генерирует речь и сохраняет в файл."""
        voice = voice or self.voice or self._resolve_voice()
        rate = rate or self.rate
        volume = volume or self.volume
        pitch = pitch or self.pitch

        t_start = time.time()
        output_path = str(output_path)

        communicate = self.edge.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
        await communicate.save(output_path)

        duration_sec = 0.0
        file_size = 0
        try:
            file_size = os.path.getsize(output_path)
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
        """Получает длительность аудио."""
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
        try:
            file_size = os.path.getsize(audio_path)
            return file_size / (128 * 1024 / 8)
        except Exception:
            pass
        return 0.0

    # ═══════════════════════════════════════════════════════
    #  КЛОНИРОВАНИЕ ГОЛОСА — ОСНОВНАЯ ФИЧА
    #  Ввод: путь к аудио файлу + текст = клонированный голос
    # ═══════════════════════════════════════════════════════

    async def clone_voice(
        self,
        text: str,
        output_path: str,
        ref_audio: str,
    ) -> Dict:
        """
        Клонирование голоса по референсному аудио файлу.

        Работает так:
          1. Берёшь аудио файл: /storage/emulated/0/Download/hello.mp3
          2. Пишешь текст который этот голос должен сказать
          3. Получаешь файл с новым текстом в этом стиле голоса

        Алгоритм:
          - Определяет пол говорящего (F0 анализ)
          - Определяет язык (из текста и пути файла)
          - Подбирает лучший голос из 150+ пресетов
          - Генерирует речь подобранным голосом

        Args:
            text: Текст, который должен сказать клонированный голос
            output_path: Куда сохранить результат
            ref_audio: Путь к аудио файлу для клонирования
        """
        if not os.path.exists(ref_audio):
            raise FileNotFoundError(f"Аудио не найден: {ref_audio}")

        file_size = os.path.getsize(ref_audio)
        print(f"  [АНАЛИЗ] Файл: {ref_audio}")
        print(f"  [АНАЛИЗ] Размер: {file_size / 1024:.1f} KB")

        # 1. Определяем пол
        gender = analyze_audio_gender(ref_audio)
        print(f"  [АНАЛИЗ] Определён пол: {gender}")

        # 2. Определяем язык
        lang = detect_language_from_path(ref_audio, text)
        print(f"  [АНАЛИЗ] Определён язык: {lang}")

        # 3. Находим лучший голос
        best = find_best_clone_voice(ref_audio, text)
        voice = best["voice"]
        print(f"  [КЛОН] Выбран голос: {voice}")
        print(f"  [КЛОН] Описание: {best['desc']}")

        # 4. Генерируем
        print(f"  [КЛОН] Генерация речи...")
        result = await self.generate(text, output_path, voice=voice)
        result["clone_gender"] = gender
        result["clone_lang"] = lang
        result["clone_source"] = ref_audio
        result["clone_preset"] = best.get("preset", "")

        return result

    async def design_voice(
        self,
        text: str,
        output_path: str,
        instruction: str,
    ) -> Dict:
        """
        Дизайн голоса по инструкции.

        Парсит: "female, soft, Russian" → подбирает голос.
        """
        voice = self.find_voice_by_description(instruction)
        if not voice:
            voice = self._resolve_voice()

        rate = self.rate
        volume = self.volume
        pitch = self.pitch

        instr_lower = instruction.lower()
        if any(w in instr_lower for w in ["fast", "быстр", "быстре"]):
            rate = "+20%"
        elif any(w in instr_lower for w in ["slow", "медл", "медле"]):
            rate = "-20%"
        if any(w in instr_lower for w in ["loud", "громк", "громче"]):
            volume = "+30%"
        elif any(w in instr_lower for w in ["quiet", "тих", "тише", "шёпот", "шепот"]):
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
        """Генерирует и проигрывает аудио."""
        import tempfile
        voice = voice or self.voice or self._resolve_voice()
        tmp = tempfile.mktemp(suffix=".mp3")
        await self.generate(text, tmp, voice=voice)
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
        try:
            os.unlink(tmp)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
#  Sync wrappers
# ═══════════════════════════════════════════════════════════════

def _run_async(coro):
    """Запускает корутину синхронно."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


def list_voices(lang: str = None, gender: str = None) -> List[VoiceInfo]:
    engine = OmniVoiceMobile()
    return _run_async(engine.list_voices(lang=lang, gender=gender))


def clone_voice(text: str, output_path: str, ref_audio: str, lang: str = DEFAULT_LANG) -> Dict:
    engine = OmniVoiceMobile(lang=lang)
    return _run_async(engine.clone_voice(text, output_path, ref_audio))


def design_voice(text: str, output_path: str, instruction: str, lang: str = DEFAULT_LANG) -> Dict:
    engine = OmniVoiceMobile(lang=lang)
    return _run_async(engine.design_voice(text, output_path, instruction))
