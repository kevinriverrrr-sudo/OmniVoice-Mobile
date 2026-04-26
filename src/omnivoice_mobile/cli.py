"""
OmniVoice Mobile v2.0 — CLI entry point.

Консольная команда `omnivoice` с красивым выводом через rich.

Использование:
    omnivoice -t "Hello world" -o out.mp3
    omnivoice -t "Привет мир" -l ru -o privet.mp3
    omnivoice --voices                     # Список голосов
    omnivoice --voices -l ru               # Русские голоса
    omnivoice --presets                    # Список пресетов
    omnivoice -t "Clone" --preset female_ru_1 -o out.mp3
    omnivoice -t "Design" --instruct "female, soft, Russian" -o out.mp3
    omnivoice --info                       # Инфо об устройстве
"""

import sys
import os
import asyncio
import argparse
import textwrap

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.text import Text
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from omnivoice_mobile.engine import (
    OmniVoiceMobile,
    VERSION,
    BANNER,
    VOICE_PRESETS,
    LANG_MAP,
    RU_NAMES,
    get_device_info,
    VoiceInfo,
)

console = Console() if HAS_RICH else None


def print_banner():
    """Печатает баннер."""
    if HAS_RICH:
        console.print(BANNER)
    else:
        print(f"\n  OmniVoice Mobile v{VERSION}")
        print("  Edge TTS for Termux / Android ARM64")
        print("  400+ Voices | 75+ Languages\n")


def print_error(msg: str):
    if HAS_RICH:
        console.print(f"[bold red][ERROR][/bold red] {msg}")
    else:
        print(f"[ERROR] {msg}")


def print_success(msg: str):
    if HAS_RICH:
        console.print(f"[bold green][OK][/bold green] {msg}")
    else:
        print(f"[OK] {msg}")


def print_info(msg: str):
    if HAS_RICH:
        console.print(f"[cyan][INFO][/cyan] {msg}")
    else:
        print(f"[INFO] {msg}")


def print_warning(msg: str):
    if HAS_RICH:
        console.print(f"[bold yellow][!][/bold yellow] {msg}")
    else:
        print(f"[!] {msg}")


def normalize_lang(lang: str) -> str:
    lang = lang.strip().lower()
    return RU_NAMES.get(lang, lang)


async def cmd_voices(args):
    """Показывает список доступных голосов."""
    lang_filter = args.lang if hasattr(args, 'lang') and args.lang else None
    gender_filter = args.gender if hasattr(args, 'gender') and args.gender else None

    if lang_filter:
        lang_filter = normalize_lang(lang_filter)

    print_info("Загрузка списка голосов с серверов Microsoft...")
    engine = OmniVoiceMobile()
    voices = await engine.list_voices(lang=lang_filter, gender=gender_filter)

    if not voices:
        print_warning("Голоса не найдены.")
        return

    if HAS_RICH:
        table = Table(title=f"Доступные голосов: {len(voices)}",
                      box=box.ROUNDED, show_lines=False, title_style="bold cyan")
        table.add_column("Голос", style="bold green", min_width=30)
        table.add_column("Локаль", style="yellow", min_width=10)
        table.add_column("Пол", style="blue", min_width=8)

        for v in voices[:100]:  # Max 100 rows
            table.add_row(v.short_name, v.locale, v.gender)

        if len(voices) > 100:
            table.add_row(f"... и ещё {len(voices)-100}", "", "")

        console.print(table)
    else:
        print(f"\n  {'Голос':<35} {'Локаль':<12} {'Пол':<8}")
        print(f"  {'─'*35} {'─'*12} {'─'*8}")
        for v in voices[:50]:
            print(f"  {v.short_name:<35} {v.locale:<12} {v.gender:<8}")
        if len(voices) > 50:
            print(f"  ... и ещё {len(voices)-50}")
        print()


async def cmd_presets(args):
    """Показывает список пресетов голосов."""
    if HAS_RICH:
        table = Table(title="Пресеты голосов для клонирования",
                      box=box.ROUNDED, show_lines=False, title_style="bold cyan")
        table.add_column("Пресет", style="bold magenta", min_width=20)
        table.add_column("Голос Edge TTS", style="bold green", min_width=30)
        table.add_column("Описание", style="yellow", min_width=30)

        for name, preset in sorted(VOICE_PRESETS.items()):
            table.add_row(name, preset["voice"], preset["desc"])

        console.print(table)
    else:
        print(f"\n  {'Пресет':<20} {'Голос':<35} {'Описание'}")
        print(f"  {'─'*20} {'─'*35} {'─'*30}")
        for name, preset in sorted(VOICE_PRESETS.items()):
            print(f"  {name:<20} {preset['voice']:<35} {preset['desc']}")
        print()


async def cmd_info(args):
    """Показывает информацию об устройстве."""
    info = get_device_info()

    if HAS_RICH:
        table = Table(title="OmniVoice Mobile — Device Info",
                      box=box.ROUNDED, title_style="bold cyan")
        table.add_column("Параметр", style="bold", min_width=20)
        table.add_column("Значение", style="green", min_width=30)

        for k, v in info.items():
            if isinstance(v, float):
                v = f"{v:.1f} GB" if "gb" in k else f"{v:.2f}"
            table.add_row(str(k), str(v))

        console.print(table)

        # Show supported languages
        lang_table = Table(title="Поддерживаемые языки",
                           box=box.ROUNDED, title_style="bold cyan")
        lang_table.add_column("Код", style="bold", min_width=6)
        lang_table.add_column("Локаль", style="yellow", min_width=10)
        lang_table.add_column("Голос по умолчанию", style="green", min_width=30)

        for code, (locale, voice) in sorted(LANG_MAP.items()):
            lang_table.add_row(code, locale, voice)

        console.print(lang_table)
    else:
        print(f"\n  OmniVoice Mobile — Device Info")
        print(f"  {'='*50}")
        for k, v in info.items():
            print(f"  {k:20s} {v}")
        print()


async def cmd_generate(args):
    """Генерация речи."""
    text = args.text
    output = args.output

    if not text:
        print_error("Укажите текст: -t \"Ваш текст\"")
        sys.exit(1)

    if not output:
        # Автоматическое имя файла
        output = "omnivoice_output.mp3"

    lang = normalize_lang(args.lang) if args.lang else "en"
    voice = args.voice if hasattr(args, 'voice') and args.voice else None
    preset = args.preset if hasattr(args, 'preset') and args.preset else None
    instruct = args.instruct if hasattr(args, 'instruct') and args.instruct else None
    ref_audio = args.ref_audio if hasattr(args, 'ref_audio') and args.ref_audio else None
    ref_text = args.ref_text if hasattr(args, 'ref_text') and args.ref_text else None
    rate = args.rate if hasattr(args, 'rate') and args.rate else "+0%"
    volume = args.volume if hasattr(args, 'volume') and args.volume else "+0%"
    pitch = args.pitch if hasattr(args, 'pitch') and args.pitch else "+0Hz"

    # Определяем метод генерации
    engine = OmniVoiceMobile(voice=voice, lang=lang, rate=rate, volume=volume, pitch=pitch)

    result = None

    try:
        # Клонирование голоса
        if preset:
            if HAS_RICH:
                console.print(Panel(
                    f"[bold]Клонирование голоса[/bold]\n"
                    f"Пресет: [magenta]{preset}[/magenta]\n"
                    f"Текст: [green]{text[:60]}{'...' if len(text)>60 else ''}[/green]",
                    title="[cyan]Voice Clone[/cyan]", box=box.ROUNDED
                ))
            result = await engine.clone_voice(text, output, preset=preset)

        # Дизайн голоса
        elif instruct:
            if HAS_RICH:
                console.print(Panel(
                    f"[bold]Дизайн голоса[/bold]\n"
                    f"Инструкция: [magenta]{instruct}[/magenta]\n"
                    f"Текст: [green]{text[:60]}{'...' if len(text)>60 else ''}[/green]",
                    title="[cyan]Voice Design[/cyan]", box=box.ROUNDED
                ))
            result = await engine.design_voice(text, output, instruct)

        # Клонирование через ref_audio (подбор по описанию)
        elif ref_audio:
            desc = ref_text or lang
            if HAS_RICH:
                console.print(Panel(
                    f"[bold]Клонирование голоса[/bold]\n"
                    f"Референс: [magenta]{ref_audio}[/magenta]\n"
                    f"Описание: [yellow]{desc}[/yellow]\n"
                    f"Текст: [green]{text[:60]}{'...' if len(text)>60 else ''}[/green]",
                    title="[cyan]Voice Clone[/cyan]", box=box.ROUNDED
                ))
            result = await engine.clone_voice(text, output, description=desc)

        # Обычная генерация
        else:
            if HAS_RICH:
                console.print(Panel(
                    f"[bold]Генерация речи[/bold]\n"
                    f"Язык: [yellow]{lang}[/yellow]\n"
                    f"Голос: [magenta]{engine._resolve_voice()}[/magenta]\n"
                    f"Текст: [green]{text[:60]}{'...' if len(text)>60 else ''}[/green]",
                    title="[cyan]TTS[/cyan]", box=box.ROUNDED
                ))

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Генерация речи...", total=None)
                result = await engine.generate(text, output)
                progress.update(task, completed=True, description="Готово!")

    except Exception as e:
        print_error(f"Ошибка генерации: {e}")
        sys.exit(1)

    # Показываем результат
    if result:
        if HAS_RICH:
            console.print(Panel(
                f"[bold green]Сохранено:[/bold green] [white]{result['output']}[/white]\n"
                f"[bold]Голос:[/bold] {result['voice']}\n"
                f"[bold]Длительность:[/bold] {result['duration_sec']:.1f} сек\n"
                f"[bold]Размер:[/bold] {result['file_size'] / 1024:.1f} KB\n"
                f"[bold]Время генерации:[/bold] {result['gen_time']:.2f} сек\n"
                f"[bold]RTF:[/bold] {result['rtf']:.3f}",
                title="[bold cyan]Результат[/bold cyan]",
                box=box.DOUBLE,
            ))
        else:
            print(f"\n  Сохранено: {result['output']}")
            print(f"  Голос: {result['voice']}")
            print(f"  Длительность: {result['duration_sec']:.1f} сек")
            print(f"  Размер: {result['file_size'] / 1024:.1f} KB")
            print(f"  Время: {result['gen_time']:.2f} сек")
            print()


def cli_main():
    """Главная CLI функция."""
    parser = argparse.ArgumentParser(
        prog="omnivoice",
        description=(
            "OmniVoice Mobile v2.0 — TTS для Termux/Android\n"
            "Edge TTS Backend | 400+ Голосов | 75+ Языков | 0 ML зависимостей\n\n"
            "GitHub: https://github.com/kevinriverrrr-sudo/OmniVoice-Mobile"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Примеры:
          omnivoice -t "Hello world" -o hello.mp3
          omnivoice -t "Привет мир" -l ru -o privet.mp3
          omnivoice -t "こんにちは" -l ja -o konnichiwa.mp3
          omnivoice --voices                     Список всех голосов
          omnivoice --voices -l ru -g Female     Русские женские голоса
          omnivoice --presets                    Доступные пресеты
          omnivoice -t "Test" --preset female_ru_1 -o out.mp3
          omnivoice -t "Test" --instruct "female, soft, Russian" -o out.mp3
          omnivoice -t "Test" --ref-audio ref.wav --ref-text "Привет" -o out.mp3
          omnivoice -t "Быстрый" --rate +30% -o fast.mp3
          omnivoice -t "Тихий" --volume -20% -o quiet.mp3
          omnivoice --info                       Инфо об устройстве
        """),
    )

    # Основные аргументы
    parser.add_argument("--text", "-t", type=str, help="Текст для генерации")
    parser.add_argument("--output", "-o", type=str, help="Выходной файл (.mp3 или .wav)")
    parser.add_argument("--voice", type=str, help="Голос (напр. ru-RU-DmitryNeural)")
    parser.add_argument("--lang", "-l", type=str, default="en", help="Код языка (en, ru, zh, ja...)")
    parser.add_argument("--preset", type=str, help="Пресет голоса (см. --presets)")
    parser.add_argument("--instruct", type=str, help="Дизайн голоса (напр. 'female, soft, Russian')")
    parser.add_argument("--ref-audio", type=str, help="Референсное аудио для клонирования")
    parser.add_argument("--ref-text", type=str, help="Описание референсного голоса")
    parser.add_argument("--rate", type=str, default="+0%", help="Скорость ('+20%%', '-10%%')")
    parser.add_argument("--volume", type=str, default="+0%", help="Громкость ('+20%%', '-10%%')")
    parser.add_argument("--pitch", type=str, default="+0Hz", help="Тон ('+5Hz', '-5Hz')")

    # Команды
    parser.add_argument("--voices", action="store_true", help="Показать список голосов")
    parser.add_argument("--presets", action="store_true", help="Показать пресеты голосов")
    parser.add_argument("--info", action="store_true", help="Инфо об устройстве и языках")
    parser.add_argument("--version", "-v", action="version", version=f"OmniVoice Mobile v{VERSION}")
    parser.add_argument("--gender", "-g", type=str, help="Фильтр: Male или Female (для --voices)")

    args = parser.parse_args()

    # Баннер (всегда, кроме --version)
    print_banner()

    # Info
    if args.info:
        asyncio.run(cmd_info(args))
        return

    # Voices list
    if args.voices:
        asyncio.run(cmd_voices(args))
        return

    # Presets
    if args.presets:
        asyncio.run(cmd_presets(args))
        return

    # Генерация
    if args.text:
        asyncio.run(cmd_generate(args))
        return

    # Нет аргументов — показать помощь
    parser.print_help()


def main():
    """Точка входа."""
    try:
        cli_main()
    except KeyboardInterrupt:
        print("\n  Прервано.")
        sys.exit(0)
    except Exception as e:
        print_error(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
