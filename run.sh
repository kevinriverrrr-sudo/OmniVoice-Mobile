#!/data/data/com.termux/files/usr/bin/bash
# ================================================================
# Quick-start скрипт для быстрого запуска OmniVoice Mobile
# ================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/src"

if [ ! -f "$SRC_DIR/omnivoice_mobile.py" ]; then
    echo "Ошибка: omnivoice_mobile.py не найден в $SRC_DIR"
    echo "Убедитесь что запускаете из директории OmniVoice-Mobile"
    exit 1
fi

echo "OmniVoice Mobile — Quick Start"
echo "================================"
echo ""

# Показать инфо
echo "Информация об устройстве:"
python3 "$SRC_DIR/omnivoice_mobile.py" --info
echo ""

# Запуск с параметрами из аргументов или по умолчанию
python3 "$SRC_DIR/omnivoice_mobile.py" "$@"
