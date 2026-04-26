# Security Policy

## Supported Versions

| Версия | Поддержка |
|--------|-----------|
| 1.0.x  | ✅ Active |
| < 1.0  | ❌ EOL |

## Reporting a Vulnerability

Если вы обнаружили уязвимость:

1. **НЕ** открывайте публичный Issue
2. Отправьте email: omnivoice-mobile@proton.me
3. Опишите:
   - Тип уязвимости
   - Шаги для воспроизведения
   - Влияние
   - Предлагаемое исправление (если есть)
4. Мы ответим в течение 48 часов
5. Координируем исправление и публикацию

## Security Considerations for Mobile

### Model Download
- Модели скачиваются с HuggingFace (HTTPS)
- Проверка SHA256 хеша (в разработке)

### Termux Security
- Используйте Termux ТОЛЬКО с F-Droid
- Не предоставляйте root-доступ скриптам без проверки
- Храните API токены в `~/.local/share/` с ограниченными правами

### Resource Exhaustion
- Модель загружается целиком в RAM
- На устройствах с малой RAM возможно OOM
- Используйте swap-файл для защиты
- Монорьте: `watch -n 1 free -m`
