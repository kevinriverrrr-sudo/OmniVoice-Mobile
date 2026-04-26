#!/data/data/com.termux/files/usr/bin/bash
# ═══════════════════════════════════════════════════════════════
#  OmniVoice Mobile v2.0 — ONE-COMMAND INSTALL
#  Запуск: curl -fsSL https://raw.githubusercontent.com/kevinriverrrr-sudo/OmniVoice-Mobile/main/scripts/bootstrap.sh | bash
# ═══════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       OmniVoice Mobile v2.0 — Auto-Installer          ║"
echo "║       Edge TTS for Termux / Android ARM64              ║"
echo "║       400+ Voices | 75+ Languages | 0 ML Dependencies ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── 0. Проверка Termux ──
if [ ! -d "/data/data/com.termux" ]; then
    echo -e "${RED}[!] Это скрипт для Termux. Запустите его в Termux на Android.${NC}"
    exit 1
fi

# ── 1. Обновление пакетов ──
echo -e "${BLUE}[1/6] Обновление пакетов Termux...${NC}"
pkg update -y 2>/dev/null | tail -1
pkg upgrade -y 2>/dev/null | tail -1

# ── 2. Установка git (ОБЯЗАТЕЛЬНО до pip install git+...) ──
echo -e "${BLUE}[2/6] Установка git...${NC}"
if ! command -v git &>/dev/null; then
    pkg install -y git 2>/dev/null | tail -3
    echo -e "${GREEN}  git установлен${NC}"
else
    echo -e "${GREEN}  git уже есть${NC}"
fi

# ── 3. Системные зависимости ──
echo -e "${BLUE}[3/6] Системные зависимости...${NC}"
pkg install -y python python-pip openssl 2>/dev/null | tail -3

# Устанавливаем ffmpeg для аудио (по желанию)
if ! command -v ffmpeg &>/dev/null; then
    echo -e "${YELLOW}  Устанавливаю ffmpeg (для аудио обработки)...${NC}"
    pkg install -y ffmpeg 2>/dev/null | tail -3 || echo -e "${YELLOW}  ffmpeg не установлен (необязательно)${NC}"
else
    echo -e "${GREEN}  ffmpeg уже есть${NC}"
fi

# ── 4. Swap (если RAM < 6GB) ──
echo -e "${BLUE}[4/6] Проверка RAM...${NC}"
TOTAL_RAM=$(awk '/MemTotal/ {printf "%.0f", $2/1024}' /proc/meminfo 2>/dev/null || echo "0")
echo -e "${GREEN}  RAM: ${TOTAL_RAM} MB${NC}"

if [ "$TOTAL_RAM" -lt 6000 ]; then
    if [ ! -f ~/swapfile ]; then
        echo -e "${YELLOW}  Создаю swap (4 GB)...${NC}"
        fallocate -l 4G ~/swapfile 2>/dev/null && chmod 600 ~/swapfile
        echo -e "${YELLOW}  Swap создан. Для активации нужен root:${NC}"
        echo -e "${YELLOW}  su -c 'swapon ~/swapfile'${NC}"
    else
        echo -e "${GREEN}  Swap файл существует${NC}"
    fi
else
    echo -e "${GREEN}  RAM достаточно (>6 GB)${NC}"
fi

# ── 5. pip install OmniVoice Mobile ──
echo -e "${BLUE}[5/6] Установка OmniVoice Mobile...${NC}"
pip install --upgrade pip setuptools wheel 2>/dev/null | tail -1

echo -e "${CYAN}  pip install git+https://github.com/kevinriverrrr-sudo/OmniVoice-Mobile.git${NC}"
pip install git+https://github.com/kevinriverrrr-sudo/OmniVoice-Mobile.git

# ── 6. Проверка ──
echo -e "${BLUE}[6/6] Проверка установки...${NC}"
echo ""

# Добавляем ~/.local/bin в PATH если нужно
if [ -d "$HOME/.local/bin" ] && ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    export PATH="$HOME/.local/bin:$PATH"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    echo -e "${GREEN}  ~/.local/bin добавлен в PATH${NC}"
fi

if command -v omnivoice &>/dev/null; then
    echo -e "${GREEN}${BOLD}  omnivoice установлен!${NC}${NC}"
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║  УСПЕХ! OmniVoice Mobile v2.0 установлен.           ║${NC}${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BOLD}Быстрый старт:${NC}"
    echo ""
    echo -e "  ${GREEN}omnivoice${NC} -t \"Hello world\" -o hello.mp3"
    echo -e "  ${GREEN}omnivoice${NC} -t \"Привет мир\" -l ru -o privet.mp3"
    echo -e "  ${GREEN}omnivoice${NC} -t \"こんにちは\" -l ja -o konnichiwa.mp3"
    echo ""
    echo -e "  ${BOLD}Голоса:${NC}"
    echo -e "  ${GREEN}omnivoice${NC} --voices"
    echo -e "  ${GREEN}omnivoice${NC} --voices -l ru -g Female"
    echo ""
    echo -e "  ${BOLD}Клонирование голоса:${NC}"
    echo -e "  ${GREEN}omnivoice${NC} --presets"
    echo -e "  ${GREEN}omnivoice${NC} -t \"Текст\" --preset female_ru_1 -o out.mp3"
    echo ""
    echo -e "  ${BOLD}Дизайн голоса:${NC}"
    echo -e "  ${GREEN}omnivoice${NC} -t \"Hello\" --instruct \"female, soft, British\" -o out.mp3"
    echo ""
    echo -e "  ${BOLD}Инфо:${NC}"
    echo -e "  ${GREEN}omnivoice${NC} --info"
    echo ""
else
    echo -e "${RED}  [!] omnivoice не найден в PATH${NC}"
    echo -e "  Попробуйте:${YELLOW}"
    echo -e "    export PATH=\$PATH:\$HOME/.local/bin${NC}"
    echo -e "    или закройте и откройте Termux${NC}"
    echo ""
    echo -e "  Переустановка:${YELLOW}"
    echo -e "    pip install --force-reinstall git+https://github.com/kevinriverrrr-sudo/OmniVoice-Mobile.git${NC}"
fi
