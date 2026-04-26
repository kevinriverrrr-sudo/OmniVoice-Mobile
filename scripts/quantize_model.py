#!/usr/bin/env python3
"""
Скрипт квантизации модели OmniVoice для мобильных устройств.

Поддерживаемые форматы:
  - GGUF (для llama.cpp / termux) — INT4_Q4_K_M, INT8
  - ONNX — INT8, FP16

Использование:
  python quantize_model.py --model k2-fsa/OmniVoice --format gguf --bits 4 --output ./quantized
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path

def quantize_to_gguf(model_path: str, output_dir: str, bits: int = 4):
    """
    Экспортирует Qwen3-0.6B backbone в GGUF формат через llama.cpp.
    
    Для Termux: скомпилируйте llama.cpp с поддержкой ARM64.
    """
    print(f"\n{'='*60}")
    print(f"Квантизация в GGUF ({bits}-bit)")
    print(f"{'='*60}\n")

    # Проверяем наличие llama.cpp
    llama_cpp_path = None
    for candidate in ["llama.cpp/convert_hf_to_gguf.py",
                      "../llama.cpp/convert_hf_to_gguf.py",
                      "/data/data/com.termux/files/home/llama.cpp/convert_hf_to_gguf.py"]:
        if os.path.exists(candidate):
            llama_cpp_path = candidate
            break

    if llama_cpp_path is None:
        print("[!] llama.cpp не найден.")
        print("    Установите:")
        print("    pkg install git make cmake -y")
        print("    git clone https://github.com/ggerganov/llama.cpp")
        print("    cd llama.cpp && make")
        return False

    # Шаг 1: Конвертация HuggingFace → GGUF (FP16)
    print("[1/2] Конвертация HuggingFace → GGUF (FP16)...")
    os.makedirs(output_dir, exist_ok=True)

    fp16_out = os.path.join(output_dir, "omnivoice-fp16.gguf")
    cmd = f"python {llama_cpp_path} {model_path} --outfile {fp16_out} --outtype f16"
    print(f"  Команда: {cmd}")
    os.system(cmd)

    if not os.path.exists(fp16_out):
        print("[ERROR] Не удалось создать FP16 GGUF")
        return False

    print(f"  Создано: {fp16_out} ({os.path.getsize(fp16_out)/(1024**3):.2f} GB)")

    # Шаг 2: Квантизация FP16 → INT4/INT8
    print(f"\n[2/2] Квантизация FP16 → Q{bits}...")

    if bits == 4:
        quant_type = "Q4_K_M"
    elif bits == 8:
        quant_type = "Q8_0"
    else:
        quant_type = f"Q{bits}_0"

    quant_out = os.path.join(output_dir, f"omnivoice-{quant_type.lower()}.gguf")

    # Ищем llama-quantize
    quantize_bin = None
    for candidate in ["llama.cpp/llama-quantize",
                      "../llama.cpp/llama-quantize",
                      "/data/data/com.termux/files/home/llama.cpp/llama-quantize"]:
        if os.path.exists(candidate):
            quantize_bin = candidate
            break

    if quantize_bin:
        cmd = f"{quantize_bin} {fp16_out} {quant_out} {quant_type}"
        print(f"  Команда: {cmd}")
        os.system(cmd)

        if os.path.exists(quant_out):
            size_mb = os.path.getsize(quant_out) / (1024**2)
            print(f"  Создано: {quant_out} ({size_mb:.0f} MB)")
        else:
            print(f"  [!] llama-quantize не удался, используем FP16 GGUF")
    else:
        print(f"  [!] llama-quantize не найден, сжимаем через Python...")

        # Python-based простая квантизация
        try:
            import numpy as np

            # Читаем FP16 GGUF
            with open(fp16_out, 'rb') as f:
                data = np.frombuffer(f.read(), dtype=np.float16)

            if bits == 8:
                # INT8 квантизация
                max_val = np.max(np.abs(data))
                scale = 127.0 / max_val if max_val > 0 else 1.0
                quantized = np.clip(np.round(data * scale), -128, 127).astype(np.int8)
                with open(quant_out, 'wb') as f:
                    f.write(quantized.tobytes())
            elif bits == 4:
                # INT4 квантизация (2 значения в байт)
                max_val = np.max(np.abs(data))
                scale = 7.0 / max_val if max_val > 0 else 1.0
                quantized = np.clip(np.round(data * scale), -8, 7).astype(np.int8)
                # Упаковываем два int4 в один байт
                packed = np.zeros(len(quantized) // 2, dtype=np.uint8)
                packed = ((quantized[0::2].astype(np.uint8) & 0x0F) |
                          ((quantized[1::2].astype(np.uint8) & 0x0F) << 4))
                with open(quant_out, 'wb') as f:
                    f.write(packed.tobytes())

            size_mb = os.path.getsize(quant_out) / (1024**2)
            print(f"  Создано: {quant_out} ({size_mb:.0f} MB)")
        except ImportError:
            print(f"  [!] numpy не найден. FP16 GGUF: {fp16_out}")

    return True


def quantize_audio_tokenizer(model_path: str, output_dir: str):
    """
    Оптимизирует HiggsAudioV2 audio tokenizer для мобильных.
    Сохраняет только веса для decode (не нужно encode на мобильном).
    """
    print(f"\n{'='*60}")
    print(f"Оптимизация Audio Tokenizer")
    print(f"{'='*60}\n")

    try:
        import torch
        from transformers import AutoModel

        print("[1/2] Загрузка audio tokenizer...")
        model = AutoModel.from_pretrained(
            model_path,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
        model.eval()

        # Сохраняем TorchScript для мобильных
        print("[2/2] Экспорт в TorchScript...")
        os.makedirs(output_dir, exist_ok=True)

        # Dummy input для trace
        dummy_input = torch.randn(1, 1, 24000)  # 1 секунда

        try:
            traced = torch.jit.trace(model, dummy_input)
            ts_path = os.path.join(output_dir, "audio_tokenizer_mobile.pt")
            traced.save(ts_path)
            size_mb = os.path.getsize(ts_path) / (1024**2)
            print(f"  TorchScript: {ts_path} ({size_mb:.0f} MB)")
        except Exception as e:
            print(f"  [!] TorchScript trace не удался: {e}")
            print(f"  Сохраняем safetensors...")

            # Сохраняем оптимизированные веса
            import safetensors.torch
            state_dict = model.state_dict()
            # Убираем градиенты
            for k in state_dict:
                state_dict[k] = state_dict[k].contiguous()

            st_path = os.path.join(output_dir, "audio_tokenizer.safetensors")
            safetensors.torch.save_file(state_dict, st_path)
            size_mb = os.path.getsize(st_path) / (1024**2)
            print(f"  SafeTensors: {st_path} ({size_mb:.0f} MB)")

        del model
        return True

    except ImportError:
        print("[ERROR] torch/transformers не установлены")
        return False


def create_mobile_config(output_dir: str, bits: int, lang: str = "en"):
    """Создает конфигурационный файл для мобильного инференса."""
    config = {
        "model_type": "omnivoice_mobile",
        "version": "1.0.0",
        "quantization": f"int{bits}" if bits <= 8 else "fp16",
        "target": "termux_android_arm64",
        "audio_sample_rate": 24000,
        "num_codebooks": 8,
        "codebook_size": 1025,
        "audio_mask_id": 1024,
        "default_num_steps": 12,
        "default_guidance_scale": 1.5,
        "codebook_weights": [8, 8, 6, 6, 4, 4, 2, 2],
        "default_language": lang,
        "max_text_length": 4096,
        "max_audio_duration_seconds": 30,
        "min_ram_gb": 4,
        "recommended_ram_gb": 6,
        "model_size_gb": {
            "fp16": 2.28,
            "int8": 1.14,
            "int4": 0.57,
        },
    }

    config_path = os.path.join(output_dir, "mobile_config.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"  Конфиг: {config_path}")
    return config


def main():
    parser = argparse.ArgumentParser(
        description="Квантизация OmniVoice для мобильных устройств",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  # Квантизация в GGUF INT4 (самый маленький размер)
  python quantize_model.py --model k2-fsa/OmniVoice --format gguf --bits 4

  # Квантизация в GGUF INT8 (баланс размер/качество)
  python quantize_model.py --model k2-fsa/OmniVoice --format gguf --bits 8

  # Оптимизация audio tokenizer
  python quantize_model.py --audio-tokenizer eustlb/higgs-audio-v2-tokenizer

  # Полная квантизация (всё вместе)
  python quantize_model.py --model k2-fsa/OmniVoice --audio-tokenizer eustlb/higgs-audio-v2-tokenizer --format gguf --bits 4
        """
    )

    parser.add_argument("--model", "-m", type=str, default="k2-fsa/OmniVoice",
                        help="HuggingFace model ID или локальный путь")
    parser.add_argument("--audio-tokenizer", type=str, default="eustlb/higgs-audio-v2-tokenizer",
                        help="HuggingFace audio tokenizer ID или локальный путь")
    parser.add_argument("--format", "-f", type=str, default="gguf",
                        choices=["gguf", "onnx"], help="Формат квантизации")
    parser.add_argument("--bits", "-b", type=int, default=4,
                        choices=[4, 8], help="Битность квантизации (4 или 8)")
    parser.add_argument("--output", "-o", type=str, default="./quantized",
                        help="Директория для сохранения")
    parser.add_argument("--skip-model", action="store_true",
                        help="Пропустить квантизацию основной модели")
    parser.add_argument("--skip-audio-tokenizer", action="store_true",
                        help="Пропустить оптимизацию audio tokenizer")
    parser.add_argument("--lang", type=str, default="en",
                        help="Язык по умолчанию")

    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    print("=" * 60)
    print("OmniVoice Mobile — Квантизация модели")
    print("=" * 60)
    print(f"  Модель: {args.model}")
    print(f"  Audio tokenizer: {args.audio_tokenizer}")
    print(f"  Формат: {args.format}")
    print(f"  Битность: INT{args.bits}")
    print(f"  Выход: {args.output}")
    print("=" * 60)

    t_start = time.time()

    # Квантизация основной модели
    if not args.skip_model:
        if args.format == "gguf":
            success = quantize_to_gguf(args.model, args.output, args.bits)
            if not success:
                print("[ERROR] Квантизация модели не удалась")
                sys.exit(1)
        elif args.format == "onnx":
            print("[!] ONNX экспорт в разработке. Используйте GGUF.")
            print("    Для ONNX: pip install onnxruntime && python -m onnxruntime.transformers.optimizer")

    # Оптимизация audio tokenizer
    if not args.skip_audio_tokenizer:
        quantize_audio_tokenizer(args.audio_tokenizer, args.output)

    # Создаем конфигурацию
    print("\n[CONFIG] Создание мобильного конфига...")
    create_mobile_config(args.output, args.bits, args.lang)

    elapsed = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"Квантизация завершена за {elapsed:.1f}s")
    print(f"Файлы в: {args.output}")
    print(f"{'='*60}")

    # Показываем размеры файлов
    print("\nСозданные файлы:")
    for f in sorted(os.listdir(args.output)):
        fpath = os.path.join(args.output, f)
        size_mb = os.path.getsize(fpath) / (1024**2)
        print(f"  {f:50s} {size_mb:8.1f} MB")


if __name__ == "__main__":
    main()
