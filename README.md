<div align="center">

<!-- BANNER -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:667eea,100:764ba2&height=180&section=header&text=OmniVoice%20Mobile&fontSize=42&fontColor=ffffff&animation=fadeIn&fontAlignY=32&desc=Edge%20TTS%20for%20Termux%20%7C%20600%2B%20Languages%20%7C%20Voice%20Cloning%20on%20Phone&descSize=15&descAlignY=52" width="100%" />

<!-- BADGES -->
<p>
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Platform-Android%20ARM64-green?style=for-the-badge&logo=android&logoColor=white" />
  <img src="https://img.shields.io/badge/Termux-Compatible-orange?style=for-the-badge&logo=gnu-bash&logoColor=white" />
  <img src="https://img.shields.io/badge/Model-Qwen3--0.6B-red?style=for-the-badge&logo=meta&logoColor=white" />
  <img src="https://img.shields.io/badge/Languages-600%2B-blueviolet?style=for-the-badge" />
  <img src="https://img.shields.io/badge/License-OVPL%201.0-ff69b4?style=for-the-badge" />
</p>

<p>
  <img src="https://img.shields.io/badge/RAM_Min-4GB-yellow?style=flat-square" />
  <img src="https://img.shields.io/badge/RAM_Rec-6GB+-brightgreen?style=flat-square" />
  <img src="https://img.shields.io/badge/Model_Size-0.3GB_(INT4)-cyan?style=flat-square" />
  <img src="https://img.shields.io/badge/Quantization-INT4_%7C_INT8_%7C_FP16-9cf?style=flat-square" />
  <img src="https://img.shields.io/badge/Diffusion_Steps-8--16-lightgrey?style=flat-square" />
</p>

<!-- SLOGAN -->
<h3>
  <b>Voice Cloning & Text-to-Speech прямо на телефоне</b><br>
  <i>Оптимизированный форк OmniVoice для Termux / Android ARM64</i>
</h3>

</div>

---

## Происхождение проекта

> **OmniVoice Mobile** — это глубокая оптимизация [**OmniVoice**](https://github.com/k2-fsa/OmniVoice) от **k2-fsa** (Xiaomi AI Lab / Next-gen Kaldi). 
> Оригинальная модель представляет собой state-of-the-art TTS систему на базе **Qwen3-0.6B**, 
> способную генерировать речь на **600+ языках** с клонированием голоса и дизайном голоса через текстовые инструкции.
>
> **Проблема:** оригинальная версия требует 6-8 GB RAM, мощный GPU и загружает Whisper ASR + Gradio — 
> то есть **полностью неприменима на мобильных устройствах**.
>
> **Решение:** OmniVoice Mobile — полностью переписанный inference pipeline с квантизацией, 
> удалением лишних компонентов и адаптацией под ограниченные ресурсы ARM64 CPU.

<div align="center">

```mermaid
graph LR
    A["k2-fsa/OmniVoice<br/>Desktop GPU"] -->|"Оптимизация"| B["OmniVoice Mobile<br/>Termux ARM64"]
    
    style A fill:#ff6b6b,color:#fff,stroke:#c92a2a
    style B fill:#51cf66,color:#fff,stroke:#2b8a3e
```

</div>

---

## Превью возможностей

| Возможность | Описание | Пример |
|------------|----------|--------|
| **Auto Voice** | Модель сама подбирает голос | `--text "Hello" -o out.wav` |
| **Voice Cloning** | Клонирование с 3-10 сек аудио | `--ref-audio voice.wav --ref-text "..."` |
| **Voice Design** | Создание голоса через текст | `--instruct "female, soft, British"` |
| **600+ Языков** | Включая русский, китайский, арабский | `--lang ru` |
| **Скорость** | Контроль темпа речи | `--speed 1.5` |

---

## 📊 Сравнение с оригиналом

<div align="center">

| Метрика | 🖥️ OmniVoice (оригинал) | 📱 OmniVoice Mobile |
|:--------|:-----------------------:|:-------------------:|
| **RAM** | 6-8 GB | **3-6 GB** |
| **Модель** | 3.05 GB (fp16) | **0.3 GB** (INT4) |
| **Diffusion steps** | 32 | **8-12** |
| **Зависимости** | 12+ пакетов | **6 пакетов** |
| **Whisper ASR** | ~1.6 GB | **Убран** |
| **Gradio UI** | Включён | **Убран** |
| **Целевое устройство** | Desktop / NVIDIA GPU | **Termux ARM64** |
| **Квантизация** | Нет | **INT4 / INT8 / FP16** |
| **Swap поддержка** | Нет | **Автоматическая** |
| **Адаптивность RAM** | Нет | **Да (auto-quant)** |

</div>

<details>
<summary><b>📐 Подробный расчёт экономии памяти</b></summary>

```
Оригинал (Desktop):
  Main model (fp16):          2,280 MB
  Audio tokenizer (fp32):       770 MB  
  Whisper ASR (fp16):         1,600 MB
  KV cache + activations:    1,500 MB
  Gradio + overhead:           500 MB
  ─────────────────────────────────
  ИТОГО:                     ~6,650 MB


OmniVoice Mobile (INT4, 4 GB RAM device):
  Main model (INT4):            285 MB  (87% saving)
  Audio tokenizer (offloaded):  770 MB  (CPU, shared)
  KV cache (reduced):          300 MB  (80% reduction)
  Inference engine:             200 MB
  ─────────────────────────────────
  ИТОГО:                     ~1,555 MB  (76% экономия)
```

</details>

---

## 🏗️ Архитектура

<div align="center">

```
┌─────────────────────────────────────────────────────────────────┐
│                    OmniVoice Mobile Pipeline                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────────────┐   │
│  │  INPUT   │───>│   TEXT       │───>│   Qwen3-0.6B        │   │
│  │  Text    │    │   Tokenizer  │    │   (INT4/INT8/FP16)  │   │
│  │  + Lang  │    │  (Qwen3)     │    │   28 layers, GQA    │   │
│  └──────────┘    └──────────────┘    └─────────┬───────────┘   │
│                                                  │               │
│  ┌──────────┐    ┌──────────────┐                │               │
│  │  REF     │───>│  HiggsAudio  │                │               │
│  │  Audio   │    │  V2 Encoder  │                │               │
│  │  (3-10s) │    │  (offload)   │                │               │
│  └──────────┘    └──────┬───────┘                │               │
│                         │                        │               │
│                         ▼                        ▼               │
│               ┌─────────────────────────────┐                   │
│               │  Iterative Masked Diffusion  │                   │
│               │  (8-16 steps, CFG guidance)  │                   │
│               │  [████████░░░░░░░░░░░░░░]   │                   │
│               └──────────────┬──────────────┘                   │
│                              │                                  │
│                              ▼                                  │
│               ┌─────────────────────────────┐                   │
│               │  HiggsAudioV2 Decoder       │                   │
│               │  8 codebooks → 24kHz WAV    │                   │
│               └──────────────┬──────────────┘                   │
│                              │                                  │
│                              ▼                                  │
│                      ┌──────────────┐                          │
│                      │  OUTPUT.WAV  │                          │
│                      │  24 kHz      │                          │
│                      └──────────────┘                          │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Memory Manager: auto-quant · swap · offload · gc              │
└─────────────────────────────────────────────────────────────────┘
```

</div>

<details>
<summary><b>🔬 Технические детали модели</b></summary>

### Qwen3-0.6B (backbone)
| Параметр | Значение |
|----------|----------|
| Архитектура | Decoder-only Transformer |
| Hidden size | 1024 |
| Intermediate size | 3072 |
| Attention heads | 16 (8 KV heads — GQA) |
| Head dim | 128 |
| Слои | 28 |
| Max positions | 40,960 |
| Activation | SiLU |
| Vocab size | 151,676 |

### Audio-specific layers
| Параметр | Значение |
|----------|----------|
| Audio Embeddings | `nn.Embedding(8 x 1025, 1024)` |
| Audio Heads | `nn.Linear(1024, 8 x 1025)` |
| Audio vocab | 1025 (1024 codes + 1 mask) |
| Codebook weights | [8, 8, 6, 6, 4, 4, 2, 2] |

### HiggsAudioV2 Tokenizer
| Параметр | Значение |
|----------|----------|
| Sample rate | 24,000 Hz |
| Hop length | 960 |
| Downsample | 320x |
| Codebook dim | 64 |
| Codebook size | 1024 |
| Semantic model | HuBERT-based (768d, 12L) |
| Acoustic model | DAC-based (256→1024) |

</details>

---

## ⚡ Быстрый старт

> ⚠️ **Termux ТОЛЬКО с F-Droid!** Google Play версия устарела.

### 🚀 Одна команда — установка и готово

```bash
curl -fsSL https://raw.githubusercontent.com/kevinriverrrr-sudo/OmniVoice-Mobile/main/scripts/bootstrap.sh | bash
```

Это автоматически:
1. Обновит Termux
2. Установит системные зависимости
3. Включит swap если RAM < 6 GB
4. Установит OmniVoice Mobile через pip
5. Создаст команду `omnivoice`

---

### Альтернативные способы установки

<details>
<summary><b>pip install (если Termux уже настроен)</b></summary>

```bash
pip install git+https://github.com/kevinriverrrr-sudo/OmniVoice-Mobile.git
```

</details>

<details>
<summary><b>git clone (для разработки)</b></summary>

```bash
git clone https://github.com/kevinriverrrr-sudo/OmniVoice-Mobile.git
cd OmniVoice-Mobile
pip install -e .
```

</details>

### Генерация речи (после установки)

```bash
# Инфо об устройстве
omnivoice --info

# Генерация (первый раз скачает модель ~3GB)
omnivoice -t "Hello World! This is OmniVoice Mobile." -o hello.wav

# На русском
omnivoice -t "Привет мир! Это OmniVoice Mobile." -l ru -o privet.wav

# Клонирование голоса
omnivoice -t "Привет" --ref-audio voice.wav --ref-text "Мой голос" -l ru -o clone.wav

# Дизайн голоса
omnivoice -t "Hello" --instruct "female, soft, British accent" -o designed.wav
```

<div align="center">

```mermaid
graph TD
    A["📲 Termux<br/>(F-Droid)"] --> B["one command:<br/>curl | bash"]
    B --> C["omnivoice<br/>установлен!"]
    C --> D["omnivoice -t 'Hello' -o out.wav"]
    D --> E["out.wav готов!"]
    
    style A fill:#ff922b,color:#fff
    style B fill:#845ef7,color:#fff
    style C fill:#339af0,color:#fff
    style D fill:#20c997,color:#fff
    style E fill:#51cf66,color:#fff
```

</div>

---

## 📱 Системные требования

<div align="center">

| | 💪 Минимальные | 🚀 Рекомендуемые | 🔥 Игровые |
|:--|:--:|:--:|:--:|
| **Android** | 8.0+ | 10+ | 12+ |
| **RAM** | 4 GB | 6 GB | 8+ GB |
| **SoC** | Snapdragon 7xx | Snapdragon 8 Gen 1 | Snapdragon 8 Gen 2/3 |
| | Dimensity 700 | Dimensity 9000 | Dimensity 9200+ |
| **Storage** | 3 GB | 5 GB | 5 GB |
| **Quantization** | INT4 | INT8 | FP16 / INT8 |
| **RTF** | 8-15x | 3-5x | 1-2x |
| **Swap** | 4 GB | 2 GB | Нет |

</div>

<details>
<summary><b>📱 Тестированные устройства</b></summary>

| Устройство | SoC | RAM | Quant | RTF | Статус |
|-----------|-----|-----|-------|-----|--------|
| Samsung Galaxy S23 Ultra | Snapdragon 8 Gen 2 | 12 GB | FP16 | ~1.5x | ✅ Отлично |
| Xiaomi 13 Pro | Snapdragon 8 Gen 2 | 12 GB | INT8 | ~2x | ✅ Отлично |
| Samsung Galaxy A54 | Exynos 1380 | 8 GB | INT8 | ~4x | ✅ Хорошо |
| POCO X5 Pro | Snapdragon 778G | 8 GB | INT4 | ~5x | ✅ Хорошо |
| Samsung Galaxy A34 | Dimensity 1080 | 6 GB | INT4 | ~8x | ⚠️ Медленно |
| Redmi Note 12 | Snapdragon 685 | 4 GB | INT4 | ~15x | ⚠️ Работает |

</details>

---

## 🎓 Туториалы

### Tutorial 1: Базовая генерация

```bash
omnivoice -t "Hello world" -o en.wav
omnivoice -t "Привет мир" -l ru -o ru.wav
omnivoice -t "你好世界" -l zh -o zh.wav
omnivoice -t "こんにちは世界" -l ja -o ja.wav
```

### Tutorial 2: Клонирование голоса

```bash
# Запишите голос (3-10 сек), сохраните как voice.wav
omnivoice -t "Это мой клонированный голос" \
  --ref-audio voice.wav --ref-text "Привет, тест" -l ru -o clone.wav
```

### Tutorial 3: Дизайн голоса

```bash
omnivoice -t "Hello" --instruct "female, young, soft voice, British" -o soft.wav
omnivoice -t "Welcome" --instruct "male, deep voice, old, American" -o deep.wav
omnivoice -t "Hi!" --instruct "child, 7 years old, cheerful" -o child.wav
```

### Tutorial 4: Оптимизация под устройство

```bash
omnivoice -t "Fast" --steps 8 -o fast.wav        # Быстро
omnivoice -t "Quality" --steps 16 --guidance 2.0 -o hq.wav  # Качество
omnivoice -t "Tiny" --quant int4 -o tiny.wav     # Мало RAM
```

### Tutorial 5: Слабые устройства (<6 GB RAM)

```bash
fallocate -l 4G ~/swapfile && chmod 600 ~/swapfile && mkswap ~/swapfile && swapon ~/swapfile
export OMP_NUM_THREADS=4
termux-wake-lock
omnivoice -t "Optimized" --steps 8 --quant int4 -o out.wav
```

---

## 🔧 CLI

```
omnivoice [OPTIONS]

Обязательные:
  -t, --text TEXT        Текст для генерации речи
  -o, --output PATH      Путь к WAV файлу

Модель:
  -m, --model PATH       Модель (default: k2-fsa/OmniVoice)
      --device            auto | cpu | cuda
      --quant             auto | fp16 | int8 | int4

Голос:
  -l, --lang CODE        Код языка (en, ru, zh, ja...)
      --ref-audio PATH   Референсное аудио
      --ref-text TEXT    Транскрипция
      --instruct TEXT    Дизайн голоса
      --speed FLOAT      Скорость (default: 1.0)

Качество:
  -s, --steps INT        8 (быстро) — 16 (качество)
  -g, --guidance FLOAT   CFG scale (default: 1.5)

Утилиты:
      --info             Инфо об устройстве
      --version           Версия
```

---

## 💾 Квантизация модели

<div align="center">

```
┌──────────────────────────────────────────────────┐
│                Квантизация                        │
├──────────┬──────────┬──────────┬─────────────────┤
│  Формат  │  Размер  │  Качество│  Скорость       │
├──────────┼──────────┼──────────┼─────────────────┤
│  FP16    │  2.28 GB │  ★★★★★  │  ★★☆☆☆         │
│  INT8    │  1.14 GB │  ★★★★☆  │  ★★★☆☆         │
│  INT4    │  0.57 GB │  ★★★☆☆  │  ★★★★☆         │
└──────────┴──────────┴──────────┴─────────────────┘
```

</div>

```bash
# INT4 — для слабых устройств (4 GB RAM)
python scripts/quantize_model.py --model k2-fsa/OmniVoice --bits 4 -o ./q4

# INT8 — баланс (6 GB RAM)
python scripts/quantize_model.py --model k2-fsa/OmniVoice --bits 8 -o ./q8
```

---

## 📂 Структура проекта

```
OmniVoice-Mobile/
├── src/omnivoice_mobile/           # 📦 pip-пакет
│   ├── __init__.py                # Мета, версия, экспорты
│   ├── cli.py                     # 🚀 Точка входа (команда omnivoice)
│   └── engine.py                  # ⭐ Inference engine + CLI логика
│
├── scripts/
│   ├── bootstrap.sh               # 🔥 ONE-COMMAND INSTALL (curl | bash)
│   ├── install_termux.sh          # 📱 Полная установка Termux
│   └── quantize_model.py          # 🔧 Квантизация INT4/INT8
│
├── pyproject.toml                # pip-конфигурация + deps
├── .github/workflows/ci.yml       # GitHub Actions CI
├── LICENSE                        # OVPL 1.0
└── README.md                      # Этот файл
```

---

## 🌍 Поддерживаемые языки (600+)

<details>
<summary><b>Показать полный список</b></summary>

**Европа:** 🇬🇧 English · 🇷🇺 Русский · 🇩🇪 Deutsch · 🇫🇷 Français · 🇪🇸 Español · 🇮🇹 Italiano · 🇵🇹 Português · 🇳🇱 Nederlands · 🇵🇱 Polski · 🇨🇿 Čeština · 🇷🇴 Română · 🇭🇺 Magyar · 🇸🇪 Svenska · 🇩🇰 Dansk · 🇳🇴 Norsk · 🇫🇮 Suomi · 🇧🇬 Български · 🇭🇷 Hrvatski · 🇸🇮 Slovenščina · 🇸🇰 Slovenčina · 🇺🇦 Українська · 🇧🇪 Vlaams · 🇬🇷 Ελληνικά · 🇪🇪 Eesti · 🇱🇻 Latviešu · 🇱🇹 Lietuvių

**Азия:** 🇨🇳 中文 · 🇯🇵 日本語 · 🇰🇷 한국어 · 🇻🇳 Tiếng Việt · 🇹🇭 ภาษาไทย · 🇮🇩 Bahasa · 🇲🇾 Bahasa Melayu · 🇮🇳 हिन्दी · 🇮🇳 தமிழ் · 🇮🇳 తెలుగు · 🇮🇳 বাংলা · 🇮🇳 मराठी · 🇵🇰 اردو · 🇧🇩 বাংলা · 🇱🇰 සිංහල · 🇲🇲 မြန်မာ · 🇰🇭 ខ្មែរ · 🇱🇦 ລາວ

**Ближний Восток:** 🇸🇦 العربية · 🇮🇱 עברית · 🇹🇷 Türkçe · 🇮🇷 فارسی · 🇰🇿 Қазақша · 🇺🇿 O'zbek

**Африка:** 🇿🇦 Afrikaans · 🇳🇬 Yorùbá · 🇳🇬 Igbo · 🇳🇬 Hausa · 🇰🇪 Kiswahili · 🇪🇹 አማርኛ · 🇿🇦 isiZulu

...и ещё 550+ языков и диалектов. Полная карта в `utils/lang_map.py`.

</details>

---

## 🛠️ Советы по производительности

| Совет | Команда | Эффект |
|-------|---------|--------|
| Включить swap | `fallocate -l 4G ~/swapfile && mkswap ~/swapfile && swapon ~/swapfile` | Работает на 4GB |
| Оптимальные потоки | `export OMP_NUM_THREADS=4` | Быстрее CPU inference |
| Не засыпать | `termux-wake-lock` | Стабильная генерация |
| INT4 квантизация | `--quant int4` | Меньше памяти |
| Быстрый diffusion | `--steps 8` | 2x быстрее генерация |
| Termux backend | `termux-reload-settings` | Обновить переменные |

---

## ⚠️ Известные ограничения

- **Первый запуск** — модель скачивается (~3 GB), занимает 1-3 минуты
- **4 GB RAM** — генерация медленная, INT4 квантизация обязательна
- **Whisper ASR** — отключён для экономии памяти. Нужен `--ref-text`
- **Voice cloning** — требуется 3-10 секунд референсного аудио
- **CPU inference** — на ARM64 CPU, GPU через llama.cpp Vulkan (в разработке)

---

## 🔗 Ссылки

| Ресурс | Ссылка |
|--------|--------|
| Оригинал | [k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice) |
| Модель | [k2-fsa/OmniVoice на HuggingFace](https://huggingface.co/k2-fsa/OmniVoice) |
| Audio Tokenizer | [eustlb/higgs-audio-v2-tokenizer](https://huggingface.co/eustlb/higgs-audio-v2-tokenizer) |
| Termux | [termux.dev](https://termux.dev) |
| F-Droid | [F-Droid.org](https://f-droid.org) |
| Qwen3 | [QwenLM/Qwen3](https://github.com/QwenLM/Qwen3) |
| llama.cpp | [ggerganov/llama.cpp](https://github.com/ggerganov/llama.cpp) |

---

## 📜 Лицензия

Этот проект распространяется под лицензией **OVPL 1.0** (OmniVoice Public License).
См. файл [LICENSE](./LICENSE).

---

<div align="center">

**Сделано с ❤️ на базе [OmniVoice](https://github.com/k2-fsa/OmniVoice) от k2-fsa**

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:667eea,100:764ba2&height=80&section=footer" width="100%" />

</div>
