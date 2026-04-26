"""
OmniVoice Mobile v2.1 — CLI

Консольная команда `omnivoice`.

Автор: kevinriverrrr-sudo (GitHub)
Репозиторий: https://github.com/kevinriverrrr-sudo/OmniVoice-Mobile
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
    DEFAULT_LANG,
    AUTHOR,
    REPO,
    get_device_info,
    VoiceInfo,
)

console = Console() if HAS_RICH else None


def print_banner():
    if HAS_RICH:
        console.print(BANNER)
    else:
        print(f"\n  OmniVoice Mobile v{VERSION}")
        print(f"  Автор: {AUTHOR} | {REPO}")
        print(f"  Русский язык по умолчанию | 400+ голосов\n")


def print_error(msg):
    if HAS_RICH:
        console.print(f"[bold red][ОШИБКА][/bold red] {msg}")
    else:
        print(f"[ОШИБКА] {msg}")


def print_success(msg):
    if HAS_RICH:
        console.print(f"[bold green][ОК][/bold green] {msg}")
    else:
        print(f"[ОК] {msg}")


def print_info(msg):
    if HAS_RICH:
        console.print(f"[cyan][INFO][/cyan] {msg}")
    else:
        print(f"[INFO] {msg}")


def print_warning(msg):
    if HAS_RICH:
        console.print(f"[bold yellow][!][/bold yellow] {msg}")
    else:
        print(f"[!] {msg}")


def normalize_lang(lang):
    lang = lang.strip().lower()
    return RU_NAMES.get(lang, lang)


async def cmd_voices(args):
    """Список голосов."""
    lang_filter = args.lang if hasattr(args, 'lang') and args.lang else None
    gender_filter = args.gender if hasattr(args, 'gender') and args.gender else None

    if lang_filter:
        lang_filter = normalize_lang(lang_filter)

    print_info("Загрузка голосов с серверов Microsoft...")
    engine = OmniVoiceMobile()
    voices = await engine.list_voices(lang=lang_filter, gender=gender_filter)

    if not voices:
        print_warning("Голоса не найдены.")
        return

    if HAS_RICH:
        table = Table(title=f"Доступных голосов: {len(voices)}",
                      box=box.ROUNDED, title_style="bold cyan")
        table.add_column("Голос", style="bold green", min_width=30)
        table.add_column("Локаль", style="yellow", min_width=10)
        table.add_column("Пол", style="blue", min_width=8)
        for v in voices[:100]:
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
    """Пресеты голосов."""
    if HAS_RICH:
        table = Table(title=f"Пресеты голосов ({len(VOICE_PRESETS)}): клонирование и дизайн",
                      box=box.ROUNDED, title_style="bold cyan")
        table.add_column("Пресет", style="bold magenta", min_width=22)
        table.add_column("Голос Edge TTS", style="bold green", min_width=32)
        table.add_column("Пол", style="blue", min_width=8)
        table.add_column("Язык", style="yellow", min_width=5)
        table.add_column("Описание", style="white", min_width=28)
        for name, preset in sorted(VOICE_PRESETS.items()):
            table.add_row(name, preset["voice"], preset["gender"],
                          preset["lang"], preset["desc"])
        console.print(table)
    else:
        print(f"\n  {'Пресет':<22} {'Голос':<32} {'Пол':<8} {'Язык':<5} {'Описание'}")
        print(f"  {'─'*22} {'─'*32} {'─'*8} {'─'*5} {'─'*28}")
        for name, preset in sorted(VOICE_PRESETS.items()):
            print(f"  {name:<22} {preset['voice']:<32} {preset['gender']:<8} {preset['lang']:<5} {preset['desc']}")
        print()


async def cmd_info(args):
    """Инфо об устройстве."""
    info = get_device_info()

    if HAS_RICH:
        # Основная инфо
        table = Table(title="OmniVoice Mobile — Информация",
                      box=box.ROUNDED, title_style="bold cyan")
        table.add_column("Параметр", style="bold", min_width=22)
        table.add_column("Значение", style="green", min_width=35)
        table.add_row("Версия", info["version"])
        table.add_row("Автор", info["author"])
        table.add_row("Репозиторий", info["repo"])
        table.add_row("Движок", info["engine"])
        table.add_row("Язык по умолчанию", info["default_lang"])
        table.add_row("Пресетов голосов", str(info["total_presets"]))
        table.add_row("Языков", str(info["total_languages"]))
        table.add_row("Архитектура", info["arch"])
        table.add_row("RAM", f"{info['total_ram_gb']:.1f} GB")
        table.add_row("Python", info["python"])
        table.add_row("Termux", "Да" if info["termux"] else "Нет")
        console.print(table)

        # Языки
        lang_table = Table(title="Поддерживаемые языки",
                           box=box.ROUNDED, title_style="bold cyan")
        lang_table.add_column("Код", style="bold", min_width=6)
        lang_table.add_column("Локаль", style="yellow", min_width=10)
        lang_table.add_column("Голос по умолчанию", style="green", min_width=30)
        for code, (locale, voice) in sorted(LANG_MAP.items()):
            marker = " ★" if code == DEFAULT_LANG else ""
            lang_table.add_row(code + marker, locale, voice)
        console.print(lang_table)
    else:
        print(f"\n  OmniVoice Mobile — Информация")
        print(f"  {'='*55}")
        for k, v in info.items():
            print(f"  {k:22s} {v}")
        print()


async def cmd_clone(args):
    """Клонирование голоса — ГЛАВНАЯ ФИЧА."""
    ref_audio = args.ref_audio
    text = args.text
    output = args.output

    if not ref_audio:
        print_error("Укажите путь к аудио: --ref-audio /путь/к/файлу.mp3")
        sys.exit(1)

    if not os.path.exists(ref_audio):
        print_error(f"Файл не найден: {ref_audio}")
        print_info("Пример пути Android: /storage/emulated/0/Download/hello.mp3")
        sys.exit(1)

    if not text:
        print_error("Укажите текст: -t \"Текст который должен сказать голос\"")
        sys.exit(1)

    if not output:
        name = os.path.splitext(os.path.basename(ref_audio))[0]
        output = f"cloned_{name}.mp3"

    lang = normalize_lang(args.lang) if hasattr(args, 'lang') and args.lang else DEFAULT_LANG

    if HAS_RICH:
        console.print(Panel(
            f"[bold]Клонирование голоса[/bold]\n"
            f"[magenta]Референс:[/magenta] {ref_audio}\n"
            f"[green]Текст:[/green] {text[:80]}{'...' if len(text) > 80 else ''}\n"
            f"[yellow]Выход:[/yellow] {output}\n"
            f"[blue]Язык:[/blue] {lang}",
            title="[bold cyan]Клонирование голоса[/bold cyan]",
            box=box.DOUBLE,
        ))

    engine = OmniVoiceMobile(lang=lang)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Анализ аудио и клонирование голоса...", total=None)
            result = await engine.clone_voice(text, output, ref_audio)
            progress.update(task, completed=True, description="Готово!")
    except Exception as e:
        print_error(f"Ошибка клонирования: {e}")
        sys.exit(1)

    # Результат
    if result:
        if HAS_RICH:
            console.print(Panel(
                f"[bold green]Сохранено:[/bold green] [white]{result['output']}[/white]\n"
                f"[bold]Голос:[/bold] {result['voice']}\n"
                f"[bold]Пол:[/bold] {result.get('clone_gender', '?')}\n"
                f"[bold]Язык:[/bold] {result.get('clone_lang', '?')}\n"
                f"[bold]Длительность:[/bold] {result['duration_sec']:.1f} сек\n"
                f"[bold]Размер:[/bold] {result['file_size'] / 1024:.1f} KB\n"
                f"[bold]Время:[/bold] {result['gen_time']:.2f} сек",
                title="[bold cyan]Голос клонирован[/bold cyan]",
                box=box.DOUBLE,
            ))
        else:
            print(f"\n  Сохранено: {result['output']}")
            print(f"  Голос: {result['voice']}")
            print(f"  Пол: {result.get('clone_gender', '?')}")
            print(f"  Язык: {result.get('clone_lang', '?')}")
            print(f"  Длительность: {result['duration_sec']:.1f} сек")
            print()


async def cmd_generate(args):
    """Генерация речи."""
    text = args.text
    output = args.output or "omnivoice_output.mp3"

    if not text:
        print_error("Укажите текст: -t \"Ваш текст\"")
        sys.exit(1)

    lang = normalize_lang(args.lang) if args.lang else DEFAULT_LANG
    voice = getattr(args, 'voice', None)
    preset = getattr(args, 'preset', None)
    instruct = getattr(args, 'instruct', None)
    rate = getattr(args, 'rate', None) or "+0%"
    volume = getattr(args, 'volume', None) or "+0%"
    pitch = getattr(args, 'pitch', None) or "+0Hz"

    engine = OmniVoiceMobile(voice=voice, lang=lang, rate=rate, volume=volume, pitch=pitch)
    result = None

    try:
        if preset:
            p = engine.find_voice_by_preset(preset)
            if p and HAS_RICH:
                console.print(Panel(
                    f"[bold]Клонирование голоса[/bold]\n"
                    f"Пресет: [magenta]{preset}[/magenta]\n"
                    f"Голос: [green]{p['voice']}[/green]\n"
                    f"Текст: [green]{text[:60]}{'...' if len(text)>60 else ''}[/green]",
                    title="[cyan]Пресет[/cyan]", box=box.ROUNDED
                ))
            result = await engine.generate(text, output, voice=p["voice"] if p else None)

        elif instruct:
            if HAS_RICH:
                console.print(Panel(
                    f"[bold]Дизайн голоса[/bold]\n"
                    f"Инструкция: [magenta]{instruct}[/magenta]\n"
                    f"Текст: [green]{text[:60]}{'...' if len(text)>60 else ''}[/green]",
                    title="[cyan]Voice Design[/cyan]", box=box.ROUNDED
                ))
            result = await engine.design_voice(text, output, instruct)

        else:
            if HAS_RICH:
                resolved = engine._resolve_voice()
                console.print(Panel(
                    f"[bold]Генерация речи[/bold]\n"
                    f"Язык: [yellow]{lang}[/yellow]\n"
                    f"Голос: [magenta]{resolved}[/magenta]\n"
                    f"Текст: [green]{text[:60]}{'...' if len(text)>60 else ''}[/green]",
                    title="[cyan]TTS[/cyan]", box=box.ROUNDED
                ))
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                          console=console) as progress:
                task = progress.add_task("Генерация речи...", total=None)
                result = await engine.generate(text, output)
                progress.update(task, completed=True, description="Готово!")

    except Exception as e:
        print_error(f"Ошибка: {e}")
        sys.exit(1)

    if result:
        if HAS_RICH:
            console.print(Panel(
                f"[bold green]Сохранено:[/bold green] [white]{result['output']}[/white]\n"
                f"[bold]Голос:[/bold] {result['voice']}\n"
                f"[bold]Длительность:[/bold] {result['duration_sec']:.1f} сек\n"
                f"[bold]Размер:[/bold] {result['file_size'] / 1024:.1f} KB\n"
                f"[bold]Время:[/bold] {result['gen_time']:.2f} сек",
                title="[bold cyan]Результат[/bold cyan]",
                box=box.DOUBLE,
            ))
        else:
            print(f"\n  Сохранено: {result['output']}")
            print(f"  Голос: {result['voice']}")
            print(f"  Длительность: {result['duration_sec']:.1f} сек")
            print()


def cli_main():
    """Главная CLI."""
    parser = argparse.ArgumentParser(
        prog="omnivoice",
        description=(
            f"OmniVoice Mobile v{VERSION} — TTS для Termux/Android\n"
            f"Edge TTS Backend | 400+ Голосов | 75+ Языков | Клонирование голоса\n"
            f"Автор: {AUTHOR} | {REPO}"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(f"""
        ━━━ Клонирование голоса ━━━
          omnivoice --clone /storage/emulated/0/Download/hello.mp3 -t "Привет мир" -o out.mp3
          omnivoice --ref-audio voice.mp3 -t "Текст" -o result.mp3

        ━━━ Базовая генерация ━━━
          omnivoice -t "Hello world" -o hello.mp3
          omnivoice -t "Привет мир" -l ru -o privet.mp3
          omnivoice -t "こんにちは" -l ja -o nihon.mp3

        ━━━ Голоса ━━━
          omnivoice --voices                        Все голоса (400+)
          omnivoice --voices -l ru -g Female        Русские женские
          omnivoice --voices -l en -g Male          Английские мужские
          omnivoice --presets                       Все пресеты (150+)

        ━━━ Клонирование через пресеты ━━━
          omnivoice -t "Test" --preset ru_female_warm -o out.mp3
          omnivoice -t "Test" --preset en_male_british -o out.mp3

        ━━━ Дизайн голоса ━━━
          omnivoice -t "Hello" --instruct "female, soft, British" -o out.mp3

        ━━━ Настройки ━━━
          omnivoice -t "Быстрый" --rate +30% -o fast.mp3
          omnivoice -t "Тихий" --volume -20% -o quiet.mp3
          omnivoice -t "Высокий" --pitch +5Hz -o high.mp3

        ━━━ Утилиты ━━━
          omnivoice --info                         Инфо об устройстве
          omnivoice --version                      Версия

        Автор: {AUTHOR}
        Репозиторий: {REPO}
        """),
    )

    # Основные
    parser.add_argument("--text", "-t", type=str, help="Текст для генерации речи")
    parser.add_argument("--output", "-o", type=str, help="Выходной файл (.mp3)")
    parser.add_argument("--voice", type=str, help="Конкретный голос (ru-RU-DmitryNeural)")
    parser.add_argument("--lang", "-l", type=str, default=None,
                        help="Код языка (по умолчанию: ru)")
    parser.add_argument("--preset", type=str, help="Пресет голоса (см. --presets)")
    parser.add_argument("--instruct", type=str, help="Дизайн голоса ('female, soft, Russian')")
    parser.add_argument("--ref-audio", type=str, help="Путь к аудио для клонирования голоса")
    parser.add_argument("--clone", type=str, help="Клонирование: путь к аудио файлу",
                        metavar="AUDIO_PATH")
    parser.add_argument("--rate", type=str, default=None, help="Скорость ('+20%%', '-10%%')")
    parser.add_argument("--volume", type=str, default=None, help="Громкость ('+20%%', '-10%%')")
    parser.add_argument("--pitch", type=str, default=None, help="Тон ('+5Hz', '-5Hz')")

    # Команды
    parser.add_argument("--voices", action="store_true", help="Показать все голоса")
    parser.add_argument("--presets", action="store_true", help="Показать пресеты голосов")
    parser.add_argument("--info", action="store_true", help="Инфо об устройстве и языках")
    parser.add_argument("--version", "-v", action="version", version=f"OmniVoice Mobile v{VERSION} (c) {AUTHOR}")
    parser.add_argument("--gender", "-g", type=str, help="Фильтр: Male или Female")

    args = parser.parse_args()

    print_banner()

    # --clone = сокращение для --ref-audio
    if args.clone:
        args.ref_audio = args.clone
        if not args.output:
            name = os.path.splitext(os.path.basename(args.clone))[0]
            args.output = f"cloned_{name}.mp3"

    # Info
    if args.info:
        asyncio.run(cmd_info(args))
        return

    # Voices
    if args.voices:
        asyncio.run(cmd_voices(args))
        return

    # Presets
    if args.presets:
        asyncio.run(cmd_presets(args))
        return

    # Клонирование (ref_audio без text = ошибка)
    if args.ref_audio:
        if not args.text:
            print_error("Укажите текст который должен сказать клонированный голос:")
            print_info(f'  omnivoice --clone "{args.ref_audio}" -t "Ваш текст" -o out.mp3')
            sys.exit(1)
        asyncio.run(cmd_clone(args))
        return

    # Генерация
    if args.text:
        asyncio.run(cmd_generate(args))
        return

    # Нет аргументов — помощь
    parser.print_help()


def main():
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
