"""
OmniVoice Mobile — CLI entry point.

Устанавливается как консольная команда `omnivoice` через pip.

Использование:
    omnivoice -t "Hello world" -o out.wav
    omnivoice -t "Привет" -l ru -o privet.wav
    omnivoice -t "Clone" --ref-audio voice.wav --ref-text "text" -o clone.wav
"""

import sys
import os


def main():
    """Точка входа для консольной команды `omnivoice`."""
    # Импортируем CLI из модуля engine (main() там)
    from omnivoice_mobile.engine import cli_main
    cli_main()


if __name__ == "__main__":
    main()
