#!/data/data/com.termux/files/usr/bin/bash
# ═══════════════════════════════════════════════════════════════
#  OmniVoice Mobile — ONE-COMMAND INSTALL
#  Запуск: curl -fsSL https://raw.githubusercontent.com/kevinriverrrr-sudo/OmniVoice-Mobile/main/scripts/bootstrap.sh | bash
# ═══════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       OmniVoice Mobile — Auto-Installer                ║"
echo "║       Edge TTS for Termux / Android ARM64              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── 1. Обновление Termux ──
echo -e "${BLUE}[1/5] Обновление пакетов...${NC}"
pkg update -y 2>/dev/null | tail -1
pkg upgrade -y 2>/dev/null | tail -1

# ── 2. Системные пакеты ──
echo -e "${BLUE}[2/5] Системные зависимости...${NC}"
pkg install -y python python-pip git 2>/dev/null | tail -3

# ── 3. Swap (если RAM < 6GB) ──
TOTAL_RAM=$(awk '/MemTotal/ {printf "%.0f", $2/1024}' /proc/meminfo 2>/dev/null || echo "0")
echo -e "${BLUE}[3/5] RAM: ${TOTAL_RAM} MB${NC}"

if [ "$TOTAL_RAM" -lt 6000 ]; then
    if [ ! -f ~/swapfile ]; then
        echo -e "${YELLOW}  Включаю swap (4 GB)...${NC}"
        fallocate -l 4G ~/swapfile 2>/dev/null && chmod 600 ~/swapfile && mkswap ~/swapfile >/dev/null 2>&1
        swapon ~/swapfile 2>/dev/null && echo -e "${GREEN}  Swap включён${NC}" || echo -e "${YELLOW}  Swap требует root (нормально)${NC}"
    else
        echo -e "${GREEN}  Swap уже есть${NC}"
    fi
else
    echo -e "${GREEN}  RAM достаточно${NC}"
fi

# ── 4. pip install с GitHub ──
echo -e "${BLUE}[4/5] Установка OmniVoice Mobile (pip)...${NC}"
pip install --upgrade pip setuptools wheel 2>/dev/null | tail -1

pip install git+https://github.com/kevinriverrrr-sudo/OmniVoice-Mobile.git

# ── 5. Проверка ──
echo -e "${BLUE}[5/5] Проверка установки...${NC}"
echo ""

if command -v omnivoice &>/dev/null; then
    echo -e "${GREEN}  omnivoice установлен!${NC}"
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   УСПЕХ! OmniVoice Mobile установлен.                 ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Использование:"
    echo -e "  ${GREEN}omnivoice${NC} -t \"Hello world\" -o out.wav"
    echo -e "  ${GREEN}omnivoice${NC} -t \"Привет мир\" -l ru -o privet.wav"
    echo -e "  ${GREEN}omnivoice${NC} --info"
    echo ""
    echo -e "  Клонирование голоса:"
    echo -e "  ${GREEN}omnivoice${NC} -t \"Текст\" --ref-audio voice.wav --ref-text \"Транскрипция\" -o out.wav"
    echo ""
    echo -e "  Дизайн голоса:"
    echo -e "  ${GREEN}omnivoice${NC} -t \"Hello\" --instruct \"female, soft, British\" -o out.wav"
    echo ""

    # Показать инфо
    omnivoice --info
else
    echo -e "${RED}  [!] omnivoice не найден в PATH${NC}"
    echo -e "  Попробуйте: export PATH=\$PATH:\$HOME/.local/bin"
    echo -e "  Или переустановите: pip install --force-reinstall git+https://github.com/kevinriverrrr-sudo/OmniVoice-Mobile.git"
fi
