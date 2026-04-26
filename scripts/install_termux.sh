#!/data/data/com.termux/files/usr/bin/bash
# ================================================================
# OmniVoice Mobile — Скрипт установки для Termux / Android
# ================================================================
# Запуск: bash install_termux.sh
#
# Требования:
#   - Android 8.0+ (64-bit)
#   - Termux из F-Droid (НЕ из Google Play!)
#   - 4+ GB RAM (рекомендуется 6+ GB)
#   - 5+ GB свободного места
#
# ================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  OmniVoice Mobile — Установка для Termux        ${NC}"
echo -e "${GREEN}================================================${NC}\n"

# ──────────────────────────────────────────────
# 1. Обновление пакетов
# ──────────────────────────────────────────────
echo -e "${BLUE}[1/8] Обновление пакетов Termux...${NC}"
pkg update -y && pkg upgrade -y

# ──────────────────────────────────────────────
# 2. Установка базовых зависимостей
# ──────────────────────────────────────────────
echo -e "${BLUE}[2/8] Установка базовых пакетов...${NC}"
pkg install -y \
    python \
    python-pip \
    git \
    wget \
    curl \
    build-essential \
    cmake \
    zlib \
    libffi \
    openssl \
    ndk-sysroot \
    libandroid-support \
    termux-tools \
    openssh \
    proot \
    file

# ──────────────────────────────────────────────
# 3. Настройка окружения Python
# ──────────────────────────────────────────────
echo -e "${BLUE}[3/8] Настройка Python...${NC}"
python -m pip install --upgrade pip setuptools wheel

# ──────────────────────────────────────────────
# 4. Настройка Swap (для устройств с <6 GB RAM)
# ──────────────────────────────────────────────
TOTAL_RAM=$(awk '/MemTotal/ {printf "%.0f", $2/1024}' /proc/meminfo)

echo -e "${YELLOW}[INFO] Обнаружено RAM: ${TOTAL_RAM} MB${NC}"

if [ "$TOTAL_RAM" -lt 6000 ]; then
    echo -e "${YELLOW}[4/8] Настройка swap-файла (${TOTAL_RAM} MB RAM < 6 GB)...${NC}"
    
    # Проверяем доступно ли место
    AVAILABLE=$(df -P ~/storage | awk 'NR==2 {printf "%d", $4/1024}')
    SWAP_SIZE=4
    
    if [ "$AVAILABLE" -lt 5000 ]; then
        echo -e "${YELLOW}  Мало места, swap = 2G${NC}"
        SWAP_SIZE=2
    fi
    
    # Создаем swap
    if [ ! -f ~/swapfile ]; then
        fallocate -l ${SWAP_SIZE}G ~/swapfile
        chmod 600 ~/swapfile
        mkswap ~/swapfile
        swapon ~/swapfile 2>/dev/null || echo -e "${YELLOW}  [!] swapon требует root. Swap не активирован.${NC}"
        echo -e "${GREEN}  Swap файл создан: ~/swapfile (${SWAP_SIZE}G)${NC}"
    else
        echo -e "${GREEN}  Swap уже существует.${NC}"
    fi
else
    echo -e "${GREEN}[4/8] RAM достаточно (${TOTAL_RAM} MB), swap не нужен.${NC}"
fi

# ──────────────────────────────────────────────
# 5. Установка Python зависимостей
# ──────────────────────────────────────────────
echo -e "${BLUE}[5/8] Установка Python зависимостей...${NC}"

# PyTorch для Termux ARM64
echo "  Установка PyTorch..."
pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Критические зависимости
echo "  Установка HuggingFace libraries..."
pip install --no-cache-dir \
    transformers>=4.40.0 \
    accelerate>=0.27.0 \
    safetensors>=0.4.0 \
    huggingface_hub>=0.20.0 \
    tokenizers>=0.15.0

# Аудио зависимости
echo "  Установка audio libraries..."
pip install --no-cache-dir \
    soundfile \
    numpy \
    scipy

# Опциональные (для квантизации)
echo "  Установка утилит квантизации..."
pip install --no-cache-dir \
    bitsandbytes 2>/dev/null || echo "  [!] bitsandbytes — только для GPU"

# ──────────────────────────────────────────────
# 6. Сборка llama.cpp (для GGUF квантизации)
# ──────────────────────────────────────────────
echo -e "${BLUE}[6/8] Сборка llama.cpp (опционально)...${NC}"

if [ ! -d "$HOME/llama.cpp" ]; then
    echo "  Клонирование llama.cpp..."
    git clone --depth 1 https://github.com/ggerganov/llama.cpp.git ~/llama.cpp
    cd ~/llama.cpp
    
    echo "  Сборка для ARM64..."
    make -j$(nproc) 2>/dev/null || {
        echo -e "${YELLOW}  [!] Сборка llama.cpp не удалась. Квантизация через Python.${NC}"
    }
    cd -
else
    echo -e "${GREEN}  llama.cpp уже установлен.${NC}"
fi

# ──────────────────────────────────────────────
# 7. Скачивание модели (опционально)
# ──────────────────────────────────────────────
echo -e "${BLUE}[7/8] Проверка модели...${NC}"

MODEL_DIR="$HOME/.cache/huggingface/hub/models--k2-fsa--OmniVoice"

if [ -d "$MODEL_DIR" ]; then
    echo -e "${GREEN}  Модель уже скачана.${NC}"
else
    echo -e "${YELLOW}  Модель не найдена. Скачать? (Да/Нет)${NC}"
    echo -e "${YELLOW}  Внимание: ~3 GB скачивания!${NC}"
    echo -e "${YELLOW}  Используйте: python -c \"from huggingface_hub import snapshot_download; snapshot_download('k2-fsa/OmniVoice')\"${NC}"
    echo -e "${YELLOW}  Или скачайте заранее и распакуйте в: $MODEL_DIR${NC}"
fi

# ──────────────────────────────────────────────
# 8. Тест установки
# ──────────────────────────────────────────────
echo -e "${BLUE}[8/8] Тест установки...${NC}\n"

python3 -c "
import sys
print(f'Python: {sys.version}')

try:
    import torch
    print(f'PyTorch: {torch.__version__}')
    print(f'  CPU threads: {torch.get_num_threads()}')
except ImportError:
    print('[!] PyTorch не установлен')

try:
    import torchaudio
    print(f'torchaudio: {torchaudio.__version__}')
except ImportError:
    print('[!] torchaudio не установлен')

try:
    import transformers
    print(f'transformers: {transformers.__version__}')
except ImportError:
    print('[!] transformers не установлен')

try:
    import soundfile
    print(f'soundfile: {soundfile.__version__}')
except ImportError:
    print('[!] soundfile не установлен')

import os, platform
print(f'Архитектура: {platform.machine()}')
print(f'PID: {os.getpid()}')

with open('/proc/meminfo') as f:
    for line in f:
        if 'MemTotal' in line or 'MemAvailable' in line:
            print(f'{line.strip()}')
"

echo -e "\n${GREEN}================================================${NC}"
echo -e "${GREEN}  Установка завершена!                              ${NC}"
echo -e "${GREEN}================================================${NC}"
echo -e "\nИспользование:"
echo -e "  cd OmniVoice-Mobile/src"
echo -e "  python omnivoice_mobile.py --text 'Hello world' --output hello.wav"
echo -e ""
echo -e "  # На русском:"
echo -e "  python omnivoice_mobile.py --text 'Привет мир' --lang ru --output privet.wav"
echo -e ""
echo -e "  # Клонирование голоса:"
echo -e "  python omnivoice_mobile.py --text 'Hello' --ref-audio voice.wav --ref-text 'Some text' --output clone.wav"
echo -e ""
echo -e "  # Быстрая генерация (8 шагов вместо 12):"
echo -e "  python omnivoice_mobile.py --text 'Test' --steps 8 --output fast.wav"
echo ""
