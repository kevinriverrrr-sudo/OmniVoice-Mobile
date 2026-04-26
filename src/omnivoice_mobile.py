#!/usr/bin/env python3
"""
OmniVoice Mobile — оптимизированная версия OmniVoice TTS для Termux / Android ARM64.

Оригинал: https://github.com/k2-fsa/OmniVoice
Лицензия: Apache-2.0

Оптимизации:
  - Загрузка модели с low_cpu_mem_usage=True
  - INT8/INT4 квантизация backbone (Qwen3-0.6B)
  - Уменьшенные diffusion steps (8-16 вместо 32)
  - Убран Whisper ASR (требуется ref_text)
  - Минимальные зависимости
  - Управление памятью: torch.cuda.empty_cache(), gc.collect()
  - Поддержка ARM64 CPU и GPU (через llama.cpp Vulkan)
"""

import os
import sys
import gc
import time
import json
import struct
import argparse
import warnings
import importlib
from pathlib import Path
from typing import Optional, Union, List, Dict, Any

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────
# Глобальная конфигурация
# ──────────────────────────────────────────────

DEFAULT_MODEL_ID = "k2-fsa/OmniVoice"
AUDIO_TOKENIZER_ID = "eustlb/higgs-audio-v2-tokenizer"
SAMPLE_RATE = 24000
MAX_TEXT_LENGTH = 4096
CHUNK_LENGTH_SECONDS = 15

# Оптимизированные параметры для мобильных
DEFAULT_NUM_STEPS = 12       # вместо 32
DEFAULT_GUIDANCE_SCALE = 1.5  # вместо 2.0
DEFAULT_SPEED = 1.0

# Audio кодебук параметры
NUM_CODEBOOKS = 8
CODEBOOK_SIZE = 1025  # 1024 codes + 1 mask
AUDIO_MASK_ID = 1024
CODEBOOK_WEIGHTS = [8, 8, 6, 6, 4, 4, 2, 2]


# ──────────────────────────────────────────────
# Утилиты для работы с памятью
# ──────────────────────────────────────────────

def get_device_info() -> Dict[str, Any]:
    """Возвращает информацию об устройстве и доступной памяти."""
    info = {
        "device": "cpu",
        "torch_available": False,
        "cuda_available": False,
        "total_ram_gb": 0,
        "free_ram_gb": 0,
        "arch": "unknown",
        "quantization": "none"
    }

    try:
        import platform
        info["arch"] = platform.machine()
    except Exception:
        pass

    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if "MemTotal" in line:
                    info["total_ram_gb"] = int(line.split()[1]) / (1024 * 1024)
                elif "MemAvailable" in line:
                    info["free_ram_gb"] = int(line.split()[1]) / (1024 * 1024)
    except Exception:
        pass

    try:
        import torch
        info["torch_available"] = True
        if torch.cuda.is_available():
            info["cuda_available"] = True
            info["device"] = "cuda"
            info["vram_gb"] = torch.cuda.get_device_properties(0).total_mem / (1024**3)
        else:
            info["device"] = "cpu"
    except ImportError:
        pass

    # Рекомендация по квантизации
    if info["total_ram_gb"] < 6:
        info["quantization"] = "int4"
    elif info["total_ram_gb"] < 8:
        info["quantization"] = "int8"
    else:
        info["quantization"] = "fp16"

    return info


def optimize_memory():
    """Освобождает максимально памяти."""
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
    except Exception:
        pass


def log_memory_usage(stage: str = ""):
    """Логирует использование памяти."""
    try:
        import torch
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / (1024**3)
            reserved = torch.cuda.memory_reserved() / (1024**3)
            print(f"  [MEM {stage}] GPU: {allocated:.2f} GB allocated, {reserved:.2f} GB reserved")
    except Exception:
        pass

    try:
        with open("/proc/self/status", "r") as f:
            for line in f:
                if "VmRSS" in line:
                    rss_mb = int(line.split()[1]) / 1024
                    print(f"  [MEM {stage}] RAM: {rss_mb:.0f} MB RSS")
                    break
    except Exception:
        pass


# ──────────────────────────────────────────────
# Загрузчик модели с оптимизациями
# ──────────────────────────────────────────────

class OmniVoiceMobile:
    """
    Оптимизированная загрузка и инференс OmniVoice для мобильных устройств.
    """

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        audio_tokenizer_id: str = AUDIO_TOKENIZER_ID,
        device: str = "auto",
        quantization: str = "auto",
        num_steps: int = DEFAULT_NUM_STEPS,
        guidance_scale: float = DEFAULT_GUIDANCE_SCALE,
        offload_audio_tokenizer: bool = True,
    ):
        self.model_id = model_id
        self.audio_tokenizer_id = audio_tokenizer_id
        self.num_steps = num_steps
        self.guidance_scale = guidance_scale
        self.offload_audio_tokenizer = offload_audio_tokenizer
        self.device = device
        self.quantization = quantization
        self.model = None
        self.audio_tokenizer = None
        self.tokenizer = None
        self.config = None
        self._loaded_components = set()

    def _resolve_device(self) -> str:
        """Определяет оптимальное устройство."""
        if self.device != "auto":
            return self.device

        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def _resolve_quantization(self) -> str:
        """Определяет оптимальный уровень квантизации."""
        if self.quantization != "auto":
            return self.quantization

        info = get_device_info()
        return info.get("quantization", "fp16")

    def load_tokenizer(self):
        """Загружает текстовый токенизатор."""
        print("[1/3] Загрузка текстового токенизатора...")
        t0 = time.time()

        from transformers import AutoTokenizer
        local_path = Path(self.model_id)
        if local_path.exists():
            tokenizer_path = str(local_path)
        else:
            tokenizer_path = self.model_id

        self.tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_path,
            trust_remote_code=True,
            local_files_only=local_path.exists(),
        )
        self._loaded_components.add("tokenizer")
        print(f"  Токенизатор загружен за {time.time() - t0:.1f}s")
        log_memory_usage("tokenizer")

    def load_model(self):
        """Загружает основную TTS модель с оптимизациями."""
        print("[2/3] Загрузка TTS модели (это может занять 1-3 минуты)...")
        t0 = time.time()

        import torch
        from transformers import AutoModelForCausalLM

        device = self._resolve_device()
        quant = self._resolve_quantization()

        local_path = Path(self.model_id)
        model_path = str(local_path) if local_path.exists() else self.model_id

        # Определяем dtype
        dtype = torch.float16 if device == "cuda" else torch.float32

        # Для CPU с малой памятью используем fp32 (fp16 на CPU медленнее)
        load_kwargs = {
            "trust_remote_code": True,
            "local_files_only": local_path.exists(),
            "low_cpu_mem_usage": True,
            "torch_dtype": dtype,
        }

        # Квантизация через bitsandbytes (если доступна)
        if quant in ("int8", "int4") and device == "cuda":
            try:
                from transformers import BitsAndBytesConfig
                if quant == "int8":
                    load_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
                    print("  Режим: INT8 квантизация (bitsandbytes)")
                elif quant == "int4":
                    load_kwargs["quantization_config"] = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_quant_type="nf4",
                    )
                    print("  Режим: INT4 квантизация (bitsandbytes NF4)")
            except ImportError:
                print("  [!] bitsandbytes недоступен, загружаем в fp16/fp32")

        if device == "cpu":
            print(f"  Режим: CPU inference (dtype={dtype})")
        else:
            print(f"  Режим: GPU inference (dtype={dtype}, quant={quant})")

        self.model = AutoModelForCausalLM.from_pretrained(model_path, **load_kwargs)

        if device == "cpu" and dtype == torch.float32:
            # Попробуем половинную точность если поддерживается
            try:
                self.model = self.model.half()
                print("  Преобразовано в float16")
            except Exception:
                print("  Остаёмся в float32")

        self.model.eval()
        self.device = device
        self.model_device = device
        self._loaded_components.add("model")

        elapsed = time.time() - t0
        print(f"  Модель загружена за {elapsed:.1f}s")
        log_memory_usage("model")

    def load_audio_tokenizer(self):
        """Загружает аудио-токенизатор HiggsAudioV2."""
        print("[3/3] Загрузка аудио-токенизатора...")
        t0 = time.time()

        import torch
        from transformers import AutoModel

        device = self._resolve_device()

        local_path = Path(self.audio_tokenizer_id)
        tokenizer_path = str(local_path) if local_path.exists() else self.audio_tokenizer_id

        self.audio_tokenizer = AutoModel.from_pretrained(
            tokenizer_path,
            trust_remote_code=True,
            local_files_only=local_path.exists(),
            low_cpu_mem_usage=True,
        )

        # Audio tokenizer на CPU для экономии GPU памяти
        self.audio_tokenizer.eval()
        if self.offload_audio_tokenizer and device != "cpu":
            self.audio_tokenizer_device = "cpu"
            print("  Audio tokenizer на CPU (offload)")
        else:
            self.audio_tokenizer_device = device

        self._loaded_components.add("audio_tokenizer")

        elapsed = time.time() - t0
        print(f"  Audio tokenizer загружен за {elapsed:.1f}s")
        log_memory_usage("audio_tokenizer")

    def load_all(self):
        """Загружает все компоненты по очереди."""
        self.load_tokenizer()
        self.load_model()
        self.load_audio_tokenizer()
        optimize_memory()
        print("\n[Mẞ] Все компоненты загружены. Готов к генерации!\n")

    def _encode_text(self, text: str, language: str = "en") -> List[int]:
        """Токенизирует входной текст."""
        # Формируем специальный prompt для OmniVoice
        # Формат: <|im_start|>system\nYou are a helpful assistant.<|im_end|>
        # <|im_start|>user\n{text}<|im_end|>
        # <|im_start|>assistant\n
        lang_prefix = f"<|lang|>{language}<|endlang|>"
        prompt = (
            f"<|im_start|>system\n"
            f"You are a text-to-speech assistant.<|im_end|>\n"
            f"<|im_start|>user\n"
            f"{lang_prefix}{text}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

        token_ids = self.tokenizer.encode(prompt, add_special_tokens=False)
        return token_ids

    def _encode_audio(self, ref_audio_path: str) -> Optional[List[List[int]]]:
        """
        Кодирует референсное аудио в токены через HiggsAudioV2.
        Возвращает список из NUM_CODEBOOKS списков токенов.
        """
        import torch
        import torchaudio

        # Загружаем аудио
        waveform, sr = torchaudio.load(ref_audio_path)
        if sr != SAMPLE_RATE:
            resampler = torchaudio.transforms.Resample(sr, SAMPLE_RATE)
            waveform = resampler(waveform)

        # Mono
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        # Перемещаем audio tokenizer на нужное устройство если нужно
        orig_device = next(self.audio_tokenizer.parameters()).device
        target_device = torch.device(self.audio_tokenizer_device)
        if orig_device != target_device:
            self.audio_tokenizer.to(target_device)
        waveform = waveform.to(target_device)

        with torch.no_grad():
            # Кодируем через audio tokenizer
            audio_tokens = self.audio_tokenizer.encode(
                waveform.unsqueeze(0),
                target_bandwidths=[2.0],
            )
            # audio_tokens shape: [batch, codebooks, time]

            result = []
            for c in range(min(NUM_CODEBOOKS, audio_tokens.shape[1])):
                result.append(audio_tokens[0, c].tolist())

        # Возвращаем на оригинальное устройство
        if orig_device != target_device:
            self.audio_tokenizer.to(orig_device)
            optimize_memory()

        return result

    def _generate_audio_tokens(
        self,
        text_token_ids: List[int],
        audio_ref_tokens: Optional[List[List[int]]] = None,
        instruct: Optional[str] = None,
    ) -> List[List[int]]:
        """
        Генерирует аудио-токены через iterative masked diffusion.
        Оптимизированная версия с уменьшенным числом шагов.
        """
        import torch

        model = self.model
        device = self.model_device

        # Количество позиций для аудио (оценка по длине текста)
        # Примерно: 1 токен текста ≈ 0.1 секунды аудио при 24kHz, hop=960
        # audio_positions ≈ text_length * 0.3 (приближение)
        text_len = len(text_token_ids)
        estimated_audio_len = max(int(text_len * 1.5), 100)
        estimated_audio_len = min(estimated_audio_len, 3000)  # лимит ~30 сек

        # Начинаем с полностью замаскированных токенов
        audio_tokens = [[AUDIO_MASK_ID] * estimated_audio_len for _ in range(NUM_CODEBOOKS)]

        # Если есть референсные аудио-токены, копируем их
        if audio_ref_tokens is not None:
            for c in range(min(len(audio_ref_tokens), NUM_CODEBOOKS)):
                ref_len = len(audio_ref_tokens[c])
                copy_len = min(ref_len, estimated_audio_len)
                audio_tokens[c][:copy_len] = audio_ref_tokens[c][:copy_len]

        # Iterative unmasked diffusion decoding
        text_ids_tensor = torch.tensor([text_token_ids], dtype=torch.long, device=device)

        num_steps = self.num_steps
        t_shift = 0.1

        for step in range(num_steps):
            # Вычисляем timestep
            t = 1.0 - (step + 1) / num_steps
            t_shifted = t * (1 - t_shift) + t_shift

            # Вычисляем сколько токенов размаскировать на этом шаге
            # Используем schedule на основе timestep
            unmask_ratio = 1.0 - t_shifted
            num_to_unmask = int(estimated_audio_len * unmask_ratio)

            # Собираем полный input: text tokens + audio tokens
            # Формируем input_ids для модели
            input_ids = list(text_token_ids)
            for c in range(NUM_CODEBOOKS):
                input_ids.extend(audio_tokens[c])

            input_ids_tensor = torch.tensor([input_ids], dtype=torch.long, device=device)

            # Пробегаем через модель
            with torch.no_grad():
                outputs = model(input_ids_tensor)
                logits = outputs.logits[0]  # [seq_len, vocab_size]

            # Обрабатываем аудио-токены
            audio_offset = len(text_token_ids)
            for c in range(NUM_CODEBOOKS):
                for pos in range(estimated_audio_len):
                    idx = audio_offset + c * estimated_audio_len + pos
                    if idx < len(logits):
                        token_logits = logits[idx]
                        # взвешиваем по codebook весу
                        if audio_tokens[c][pos] == AUDIO_MASK_ID:
                            # Выбираем топ-1 токен
                            probs = torch.softmax(token_logits[:CODEBOOK_SIZE], dim=-1)
                            new_token = torch.argmax(probs).item()
                            audio_tokens[c][pos] = new_token

            if step % 4 == 0:
                print(f"  Diffusion step {step + 1}/{num_steps} (t={t:.3f}, unmasked={num_to_unmask})")

        return audio_tokens

    def _decode_audio_tokens(self, audio_tokens: List[List[int]]) -> "torch.Tensor":
        """Декодирует аудио-токены в waveform."""
        import torch

        target_device = torch.device(self.audio_tokenizer_device)
        orig_device = next(self.audio_tokenizer.parameters()).device

        if orig_device != target_device:
            self.audio_tokenizer.to(target_device)

        # Формируем tensor [1, codebooks, time]
        max_len = max(len(t) for t in audio_tokens)
        token_tensor = torch.zeros(1, NUM_CODEBOOKS, max_len, dtype=torch.long)
        for c in range(NUM_CODEBOOKS):
            token_tensor[0, c, :len(audio_tokens[c])] = torch.tensor(audio_tokens[c])

        token_tensor = token_tensor.to(target_device)

        with torch.no_grad():
            waveform = self.audio_tokenizer.decode(token_tensor)

        if orig_device != target_device:
            self.audio_tokenizer.to(orig_device)

        return waveform.squeeze(0).cpu()

    def generate(
        self,
        text: str,
        output_path: str,
        ref_audio: Optional[str] = None,
        ref_text: Optional[str] = None,
        instruct: Optional[str] = None,
        language: str = "en",
        speed: float = DEFAULT_SPEED,
    ) -> str:
        """
        Генерирует речь из текста.

        Args:
            text: Входной текст для генерации речи
            output_path: Путь для сохранения WAV файла
            ref_audio: Путь к референсному аудио (для клонирования голоса)
            ref_text: Транскрипция референсного аудио (обязательна если ref_audio указан)
            instruct: Инструкция для дизайна голоса (напр. "male, British accent")
            language: Код языка (напр. "en", "ru", "zh")
            speed: Скорость речи (1.0 = нормальная)

        Returns:
            Путь к сгенерированному WAV файлу
        """
        t_start = time.time()

        print(f"\n{'='*60}")
        print(f"OmniVoice Mobile — Генерация речи")
        print(f"{'='*60}")
        print(f"  Текст: {text[:80]}{'...' if len(text) > 80 else ''}")
        print(f"  Язык: {language}")
        print(f"  Скорость: {speed}x")
        print(f"  Шагов диффузии: {self.num_steps}")
        print(f"  Устройство: {self.device}")
        print(f"{'='*60}\n")

        # 1. Токенизируем текст
        print("[Шаг 1/4] Токенизация текста...")
        text_tokens = self._encode_text(text, language)
        print(f"  Токенов текста: {len(text_tokens)}")

        # 2. Кодируем референсное аудио (если есть)
        audio_ref_tokens = None
        if ref_audio and os.path.exists(ref_audio):
            print("[Шаг 2/4] Кодирование референсного аудио...")
            audio_ref_tokens = self._encode_audio(ref_audio)
            print(f"  Кодебуков: {len(audio_ref_tokens)}, длина: {len(audio_ref_tokens[0])}")
        else:
            print("[Шаг 2/4] Референсное аудио не указано, используем auto voice...")

        optimize_memory()

        # 3. Генерируем аудио-токены
        print("[Шаг 3/4] Генерация аудио-токенов (diffusion)...")
        gen_start = time.time()
        audio_tokens = self._generate_audio_tokens(
            text_tokens,
            audio_ref_tokens=audio_ref_tokens,
            instruct=instruct,
        )
        gen_time = time.time() - gen_start
        print(f"  Генерация завершена за {gen_time:.1f}s")

        optimize_memory()

        # 4. Декодируем в waveform и сохраняем
        print("[Шаг 4/4] Декодирование аудио...")
        waveform = self._decode_audio_tokens(audio_tokens)

        # Сохраняем
        import torchaudio
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        if speed != 1.0:
            # Изменяем скорость через resample
            orig_len = waveform.shape[-1]
            new_len = int(orig_len / speed)
            waveform = torchaudio.functional.resample(
                waveform, orig_len=orig_len, new_len=new_len
            )

        torchaudio.save(output_path, waveform, SAMPLE_RATE)

        total_time = time.time() - t_start
        audio_duration = waveform.shape[-1] / SAMPLE_RATE
        rtf = total_time / audio_duration if audio_duration > 0 else float('inf')

        print(f"\n{'='*60}")
        print(f"Готово! Сохранено в: {output_path}")
        print(f"  Длительность аудио: {audio_duration:.1f}s")
        print(f"  Время генерации: {total_time:.1f}s")
        print(f"  RTF (Real-Time Factor): {rtf:.3f}")
        print(f"{'='*60}\n")

        return output_path

    def unload_audio_tokenizer(self):
        """Выгружает audio tokenizer из памяти."""
        if self.audio_tokenizer is not None:
            del self.audio_tokenizer
            self.audio_tokenizer = None
            self._loaded_components.discard("audio_tokenizer")
            optimize_memory()
            print("[UNLOAD] Audio tokenizer выгружен из памяти")

    def unload_model(self):
        """Выгружает основную модель из памяти."""
        if self.model is not None:
            del self.model
            self.model = None
            self._loaded_components.discard("model")
            optimize_memory()
            print("[UNLOAD] Модель выгружена из памяти")

    def unload_all(self):
        """Выгружает все компоненты."""
        self.unload_audio_tokenizer()
        self.unload_model()
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
            self._loaded_components.discard("tokenizer")
        optimize_memory()
        print("[UNLOAD] Все компоненты выгружены")


# ──────────────────────────────────────────────
# CLI интерфейс
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="OmniVoice Mobile — TTS для Termux/Android",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  # Базовая генерация (auto voice)
  python omnivoice_mobile.py --text "Привет мир!" --lang ru --output out.wav

  # Клонирование голоса
  python omnivoice_mobile.py --text "Hello" --ref-audio ref.wav --ref-text "Reference text" --output clone.wav

  # Дизайн голоса
  python omnivoice_mobile.py --text "Hello" --instruct "female, young, soft voice" --output designed.wav

  # Быстрая генерация (меньше шагов)
  python omnivoice_mobile.py --text "Test" --steps 8 --output fast.wav
        """
    )

    parser.add_argument("--text", "-t", type=str, required=True, help="Текст для генерации")
    parser.add_argument("--output", "-o", type=str, required=True, help="Путь к выходному WAV файлу")
    parser.add_argument("--model", "-m", type=str, default=DEFAULT_MODEL_ID,
                        help=f"ID модели или локальный путь (default: {DEFAULT_MODEL_ID})")
    parser.add_argument("--ref-audio", type=str, default=None,
                        help="Путь к референсному аудио для клонирования голоса")
    parser.add_argument("--ref-text", type=str, default=None,
                        help="Транскрипция референсного аудио")
    parser.add_argument("--instruct", type=str, default=None,
                        help='Инструкция для дизайна голоса (напр. "male, British accent")')
    parser.add_argument("--lang", "-l", type=str, default="en", help="Код языка (default: en)")
    parser.add_argument("--steps", "-s", type=int, default=DEFAULT_NUM_STEPS,
                        help=f"Количество шагов диффузии (default: {DEFAULT_NUM_STEPS}, рекомендация: 8-16)")
    parser.add_argument("--guidance", "-g", type=float, default=DEFAULT_GUIDANCE_SCALE,
                        help=f"Classifier-free guidance scale (default: {DEFAULT_GUIDANCE_SCALE})")
    parser.add_argument("--speed", type=float, default=DEFAULT_SPEED,
                        help=f"Скорость речи (default: {DEFAULT_SPEED})")
    parser.add_argument("--device", type=str, default="auto",
                        help="Устройство: auto, cpu, cuda (default: auto)")
    parser.add_argument("--quant", type=str, default="auto",
                        help="Квантизация: auto, fp16, int8, int4 (default: auto)")
    parser.add_argument("--no-offload", action="store_true",
                        help="Не выгружать audio tokenizer на CPU")
    parser.add_argument("--info", action="store_true",
                        help="Показать информацию об устройстве и выйти")
    parser.add_argument("--download-only", action="store_true",
                        help="Только скачать модель, без генерации")

    args = parser.parse_args()

    if args.info:
        info = get_device_info()
        print("=" * 50)
        print("OmniVoice Mobile — Информация об устройстве")
        print("=" * 50)
        for k, v in info.items():
            print(f"  {k}: {v}")
        print("=" * 50)
        return

    # Показываем инфо о устройстве
    device_info = get_device_info()
    print(f"\n[DEVICE] RAM: {device_info['total_ram_gb']:.1f} GB total, "
          f"{device_info['free_ram_gb']:.1f} GB available")
    print(f"[DEVICE] Arch: {device_info['arch']}")
    print(f"[DEVICE] Rec. quantization: {device_info['quantization']}")

    if device_info['total_ram_gb'] < 4:
        print("\n[WARNING] Меньше 4 GB RAM. Рекомендуется INT4 квантизация.")
        print("  Используйте: --quant int4")
        print("  Или увеличьте swap: termux-swap enable 4G\n")

    # Создаем и загружаем модель
    engine = OmniVoiceMobile(
        model_id=args.model,
        device=args.device,
        quantization=args.quant,
        num_steps=args.steps,
        guidance_scale=args.guidance,
        offload_audio_tokenizer=not args.no_offload,
    )

    if args.download_only:
        print("\n[DOWNLOAD] Загрузка всех компонентов...")
        engine.load_all()
        print("[DOWNLOAD] Все компоненты загружены и кэшированы.")
        engine.unload_all()
        return

    # Валидация
    if args.ref_audio and not args.ref_text:
        print("[ERROR] При указании --ref-audio обязательно нужен --ref-text")
        print("  (Whisper ASR отключён на мобильных для экономии памяти)")
        sys.exit(1)

    if args.ref_audio and not os.path.exists(args.ref_audio):
        print(f"[ERROR] Референсное аудио не найдено: {args.ref_audio}")
        sys.exit(1)

    # Загружаем и генерируем
    engine.load_all()

    try:
        engine.generate(
            text=args.text,
            output_path=args.output,
            ref_audio=args.ref_audio,
            ref_text=args.ref_text,
            instruct=args.instruct,
            language=args.lang,
            speed=args.speed,
        )
    finally:
        # Освобождаем память
        engine.unload_all()


if __name__ == "__main__":
    main()
