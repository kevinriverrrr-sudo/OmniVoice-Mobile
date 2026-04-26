# Лог проекта OmniVoice Mobile

## 2026-04-26: Начальная версия

### Изучено
- Репозиторий k2-fsa/OmniVoice на GitHub
- OmniVoice — это TTS модель на базе Qwen3-0.6B
- Поддерживает 600+ языков, клонирование и дизайн голоса
- Размер модели: ~3 GB (main + audio tokenizer)
- Требует 6-8 GB RAM, 4-6 GB VRAM

### Создано
- Оптимизированный inference скрипт для Termux/ARM64
- Скрипт квантизации (GGUF INT4/INT8, ONNX)
- Аудио утилиты (замена pydub/librosa)
- Карта языков (600+)
- Скрипт установки Termux
- GGUF загрузчик через llama.cpp
- README с полной документацией

### Оптимизации
- Уменьшены diffusion steps: 32 → 12 (рекомендуется 8-16)
- Убран Whisper ASR (экономия ~1.6 GB)
- Убраны Gradio, tensorboardX, webdataset (training deps)
- low_cpu_mem_usage при загрузке
- Автоматическая выгрузка модели из памяти
- INT8/INT4 квантизация поддержка
- Audio tokenizer offload на CPU
- Swap конфигурация для устройств с малой RAM
