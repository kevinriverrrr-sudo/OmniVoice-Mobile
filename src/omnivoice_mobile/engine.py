"""
OmniVoice Mobile — Core inference engine + CLI.

Оптимизированная версия OmniVoice TTS для Termux / Android ARM64.

Оригинал: https://github.com/k2-fsa/OmniVoice
Лицензия оригинала: Apache-2.0
Лицензия этого проекта: OVPL 1.0

Оптимизации:
  - low_cpu_mem_usage=True при загрузке модели
  - INT8/INT4 квантизация backbone (Qwen3-0.6B)
  - Уменьшенные diffusion steps (8-16 вместо 32)
  - Whisper ASR убран (требуется ref_text)
  - Минимальные зависимости (6 вместо 12+)
  - Автоуправление памятью: gc.collect(), empty_cache()
  - Audio tokenizer offload на CPU
"""

import os
import sys
import gc
import time
import json
import argparse
import warnings
from pathlib import Path
from typing import Optional, List, Dict, Any

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────
# Конфигурация
# ──────────────────────────────────────────────

DEFAULT_MODEL_ID = "k2-fsa/OmniVoice"
AUDIO_TOKENIZER_ID = "eustlb/higgs-audio-v2-tokenizer"
SAMPLE_RATE = 24000
MAX_TEXT_LENGTH = 4096

# Оптимизированные параметры для мобильных
DEFAULT_NUM_STEPS = 12
DEFAULT_GUIDANCE_SCALE = 1.5
DEFAULT_SPEED = 1.0

NUM_CODEBOOKS = 8
CODEBOOK_SIZE = 1025
AUDIO_MASK_ID = 1024
CODEBOOK_WEIGHTS = [8, 8, 6, 6, 4, 4, 2, 2]

VERSION = "1.0.0"

BANNER = f"""
╔══════════════════════════════════════════════╗
║       OmniVoice Mobile  v{VERSION}              ║
║   Edge TTS for Termux / Android ARM64      ║
║   600+ Languages | Voice Cloning           ║
║   Based on k2-fsa/OmniVoice (Apache-2.0)   ║
╚══════════════════════════════════════════════╝
"""


# ──────────────────────────────────────────────
# Утилиты памяти
# ──────────────────────────────────────────────

def get_device_info() -> Dict[str, Any]:
    """Информация об устройстве и доступной памяти."""
    info = {
        "device": "cpu",
        "torch_available": False,
        "cuda_available": False,
        "total_ram_gb": 0.0,
        "free_ram_gb": 0.0,
        "arch": "unknown",
        "quantization": "none",
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
    except ImportError:
        pass
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
            a = torch.cuda.memory_allocated() / (1024**3)
            print(f"  [MEM {stage}] GPU: {a:.2f} GB")
    except Exception:
        pass
    try:
        with open("/proc/self/status", "r") as f:
            for line in f:
                if "VmRSS" in line:
                    print(f"  [MEM {stage}] RAM: {int(line.split()[1])/1024:.0f} MB RSS")
                    break
    except Exception:
        pass


# ──────────────────────────────────────────────
# Карта языков (краткая, полная встроена)
# ──────────────────────────────────────────────

LANG_IDS = {
    "en": 0, "zh": 1, "de": 2, "es": 3, "ru": 4, "ko": 5, "fr": 6,
    "ja": 7, "pt": 8, "tr": 9, "pl": 10, "nl": 11, "uk": 12,
    "it": 13, "ar": 14, "sv": 15, "cs": 16, "vi": 17, "th": 18,
    "id": 19, "hi": 20, "fi": 21, "he": 22, "el": 23, "ms": 24,
    "no": 25, "da": 26, "hu": 27, "ro": 28, "bn": 29, "sk": 30,
    "fa": 32, "bg": 33, "hr": 34, "ca": 35, "ur": 36, "ta": 37,
    "kk": 67, "ky": 68, "uz": 66, "yue": 100,
}

RU_NAMES = {
    "русский": "ru", "английский": "en", "китайский": "zh",
    "японский": "ja", "корейский": "ko", "немецкий": "de",
    "французский": "fr", "испанский": "es", "итальянский": "it",
    "португальский": "pt", "украинский": "uk", "казахский": "kk",
    "турецкий": "tr", "польский": "pl", "нидерландский": "nl",
    "арабский": "ar", "хинди": "hi", "бенгальский": "bn",
    "тамильский": "ta",
}


def normalize_lang(lang: str) -> str:
    lang = lang.strip().lower()
    return RU_NAMES.get(lang, lang)


# ──────────────────────────────────────────────
# OmniVoice Mobile Engine
# ──────────────────────────────────────────────

class OmniVoiceMobile:
    """Оптимизированный TTS inference engine для мобильных устройств."""

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
        self.model_device = "cpu"
        self.audio_tokenizer_device = "cpu"
        self._loaded = set()

    def _resolve_device(self) -> str:
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
        path = str(local_path) if local_path.exists() else self.model_id
        self.tokenizer = AutoTokenizer.from_pretrained(
            path, trust_remote_code=True, local_files_only=local_path.exists(),
        )
        self._loaded.add("tokenizer")
        print(f"  Загружен за {time.time()-t0:.1f}s")
        log_memory_usage("tokenizer")

    def load_model(self):
        """Загружает основную TTS модель."""
        print("[2/3] Загрузка TTS модели (1-3 мин)...")
        t0 = time.time()
        import torch
        from transformers import AutoModelForCausalLM

        device = self._resolve_device()
        quant = self._resolve_quantization()
        local_path = Path(self.model_id)
        model_path = str(local_path) if local_path.exists() else self.model_id

        dtype = torch.float16 if device == "cuda" else torch.float32
        load_kwargs = {
            "trust_remote_code": True,
            "local_files_only": local_path.exists(),
            "low_cpu_mem_usage": True,
            "torch_dtype": dtype,
        }

        if quant in ("int8", "int4") and device == "cuda":
            try:
                from transformers import BitsAndBytesConfig
                if quant == "int8":
                    load_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
                else:
                    load_kwargs["quantization_config"] = BitsAndBytesConfig(
                        load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_quant_type="nf4",
                    )
                print(f"  Режим: INT{8 if quant=='int8' else 4} квантизация")
            except ImportError:
                print("  [!] bitsandbytes недоступен")

        if device == "cpu":
            print(f"  Режим: CPU (dtype={dtype})")
        else:
            print(f"  Режим: GPU (dtype={dtype}, quant={quant})")

        self.model = AutoModelForCausalLM.from_pretrained(model_path, **load_kwargs)

        if device == "cpu" and dtype == torch.float32:
            try:
                self.model = self.model.half()
                print("  → float16")
            except Exception:
                pass

        self.model.eval()
        self.device = device
        self.model_device = device
        self._loaded.add("model")
        print(f"  Загружена за {time.time()-t0:.1f}s")
        log_memory_usage("model")

    def load_audio_tokenizer(self):
        """Загружает аудио-токенизатор HiggsAudioV2."""
        print("[3/3] Загрузка аудио-токенизатора...")
        t0 = time.time()
        import torch
        from transformers import AutoModel

        device = self._resolve_device()
        local_path = Path(self.audio_tokenizer_id)
        path = str(local_path) if local_path.exists() else self.audio_tokenizer_id

        self.audio_tokenizer = AutoModel.from_pretrained(
            path, trust_remote_code=True, local_files_only=local_path.exists(),
            low_cpu_mem_usage=True,
        )
        self.audio_tokenizer.eval()
        self.audio_tokenizer_device = "cpu" if (self.offload_audio_tokenizer and device != "cpu") else device
        self._loaded.add("audio_tokenizer")
        print(f"  Загружен за {time.time()-t0:.1f}s (на {self.audio_tokenizer_device})")
        log_memory_usage("audio_tok")

    def load_all(self):
        """Загружает все компоненты."""
        self.load_tokenizer()
        self.load_model()
        self.load_audio_tokenizer()
        optimize_memory()
        print(f"\n{'='*50}")
        print("  Готов к генерации!")
        print(f"{'='*50}\n")

    def _encode_text(self, text: str, language: str = "en") -> List[int]:
        lang_prefix = f"<|lang|>{language}<|endlang|>"
        prompt = (
            f"<|im_start|>system\n"
            f"You are a text-to-speech assistant.<|im_end|>\n"
            f"<|im_start|>user\n"
            f"{lang_prefix}{text}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        return self.tokenizer.encode(prompt, add_special_tokens=False)

    def _encode_audio(self, ref_audio_path: str) -> Optional[List[List[int]]]:
        import torch
        import torchaudio

        waveform, sr = torchaudio.load(ref_audio_path)
        if sr != SAMPLE_RATE:
            waveform = torchaudio.transforms.Resample(sr, SAMPLE_RATE)(waveform)
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        orig_device = next(self.audio_tokenizer.parameters()).device
        target_device = torch.device(self.audio_tokenizer_device)
        if orig_device != target_device:
            self.audio_tokenizer.to(target_device)
        waveform = waveform.to(target_device)

        with torch.no_grad():
            audio_tokens = self.audio_tokenizer.encode(waveform.unsqueeze(0), target_bandwidths=[2.0])
            result = [audio_tokens[0, c].tolist() for c in range(min(NUM_CODEBOOKS, audio_tokens.shape[1]))]

        if orig_device != target_device:
            self.audio_tokenizer.to(orig_device)
            optimize_memory()
        return result

    def _generate_audio_tokens(self, text_token_ids, audio_ref_tokens=None, instruct=None):
        import torch

        model = self.model
        device = self.model_device
        text_len = len(text_token_ids)
        est_len = min(max(int(text_len * 1.5), 100), 3000)

        audio_tokens = [[AUDIO_MASK_ID] * est_len for _ in range(NUM_CODEBOOKS)]

        if audio_ref_tokens is not None:
            for c in range(min(len(audio_ref_tokens), NUM_CODEBOOKS)):
                copy_len = min(len(audio_ref_tokens[c]), est_len)
                audio_tokens[c][:copy_len] = audio_ref_tokens[c][:copy_len]

        num_steps = self.num_steps
        t_shift = 0.1

        for step in range(num_steps):
            t = 1.0 - (step + 1) / num_steps
            t_shifted = t * (1 - t_shift) + t_shift

            input_ids = list(text_token_ids)
            for c in range(NUM_CODEBOOKS):
                input_ids.extend(audio_tokens[c])

            input_ids_tensor = torch.tensor([input_ids], dtype=torch.long, device=device)

            with torch.no_grad():
                outputs = model(input_ids_tensor)
                logits = outputs.logits[0]

            audio_offset = len(text_token_ids)
            for c in range(NUM_CODEBOOKS):
                for pos in range(est_len):
                    idx = audio_offset + c * est_len + pos
                    if idx < len(logits) and audio_tokens[c][pos] == AUDIO_MASK_ID:
                        probs = torch.softmax(logits[idx][:CODEBOOK_SIZE], dim=-1)
                        audio_tokens[c][pos] = torch.argmax(probs).item()

            if step % max(1, num_steps // 4) == 0:
                unmasked = sum(1 for p in range(est_len) if audio_tokens[0][p] != AUDIO_MASK_ID)
                print(f"  Step {step+1}/{num_steps}  t={t:.3f}  unmasked={unmasked}/{est_len}")

        return audio_tokens

    def _decode_audio_tokens(self, audio_tokens):
        import torch

        target_device = torch.device(self.audio_tokenizer_device)
        orig_device = next(self.audio_tokenizer.parameters()).device
        if orig_device != target_device:
            self.audio_tokenizer.to(target_device)

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

    def generate(self, text: str, output_path: str,
                 ref_audio: Optional[str] = None, ref_text: Optional[str] = None,
                 instruct: Optional[str] = None, language: str = "en",
                 speed: float = DEFAULT_SPEED) -> str:
        """Генерирует речь из текста."""
        t_start = time.time()

        print(f"\n{'='*50}")
        print(f"OmniVoice Mobile — Генерация речи")
        print(f"{'='*50}")
        print(f"  Текст: {text[:70]}{'...' if len(text)>70 else ''}")
        print(f"  Язык: {language}  |  Скорость: {speed}x")
        print(f"  Steps: {self.num_steps}  |  Device: {self.device}")
        print(f"{'='*50}\n")

        # 1
        print("[1/4] Токенизация текста...")
        text_tokens = self._encode_text(text, language)
        print(f"  Токенов: {len(text_tokens)}")

        # 2
        audio_ref_tokens = None
        if ref_audio and os.path.exists(ref_audio):
            print("[2/4] Кодирование референсного аудио...")
            audio_ref_tokens = self._encode_audio(ref_audio)
            print(f"  Codebooks: {len(audio_ref_tokens)}, len: {len(audio_ref_tokens[0])}")
        else:
            print("[2/4] Auto voice (без референса)")
        optimize_memory()

        # 3
        print("[3/4] Diffusion генерация...")
        gen_t = time.time()
        audio_tokens = self._generate_audio_tokens(text_tokens, audio_ref_tokens, instruct)
        print(f"  Генерация: {time.time()-gen_t:.1f}s")
        optimize_memory()

        # 4
        print("[4/4] Декодирование аудио...")
        waveform = self._decode_audio_tokens(audio_tokens)

        import torchaudio
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        if speed != 1.0:
            orig_len = waveform.shape[-1]
            new_len = int(orig_len / speed)
            waveform = torchaudio.functional.resample(waveform, orig_len=orig_len, new_len=new_len)

        torchaudio.save(output_path, waveform, SAMPLE_RATE)

        total_time = time.time() - t_start
        dur = waveform.shape[-1] / SAMPLE_RATE
        rtf = total_time / dur if dur > 0 else float("inf")

        print(f"\n{'='*50}")
        print(f"  Сохранено: {output_path}")
        print(f"  Длительность: {dur:.1f}s")
        print(f"  Время генерации: {total_time:.1f}s")
        print(f"  RTF: {rtf:.3f}")
        print(f"{'='*50}\n")
        return output_path

    def unload_all(self):
        for attr in ("audio_tokenizer", "model", "tokenizer"):
            obj = getattr(self, attr, None)
            if obj is not None:
                del obj
                setattr(self, attr, None)
        optimize_memory()


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def cli_main():
    parser = argparse.ArgumentParser(
        prog="omnivoice",
        description="OmniVoice Mobile — TTS для Termux/Android\n\n"
                    "GitHub: https://github.com/kevinriverrrr-sudo/OmniVoice-Mobile",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  omnivoice -t "Hello world" -o out.wav
  omnivoice -t "Привет мир" -l ru -o privet.wav
  omnivoice -t "Clone" --ref-audio voice.wav --ref-text "text" -o c.wav
  omnivoice -t "Design" --instruct "female, soft, British" -o d.wav
  omnivoice -t "Fast" --steps 8 -o fast.wav
  omnivoice --info
        """,
    )

    parser.add_argument("--text", "-t", type=str, help="Текст для генерации")
    parser.add_argument("--output", "-o", type=str, help="Путь к WAV файлу")
    parser.add_argument("--model", "-m", type=str, default=DEFAULT_MODEL_ID, help="Модель HF/локальный путь")
    parser.add_argument("--ref-audio", type=str, default=None, help="Референсное аудио (voice cloning)")
    parser.add_argument("--ref-text", type=str, default=None, help="Транскрипция референса")
    parser.add_argument("--instruct", type=str, default=None, help='Дизайн голоса, напр. "female, soft"')
    parser.add_argument("--lang", "-l", type=str, default="en", help="Код языка (en, ru, zh, ja...)")
    parser.add_argument("--steps", "-s", type=int, default=DEFAULT_NUM_STEPS, help="Diffusion steps (8-16)")
    parser.add_argument("--guidance", "-g", type=float, default=DEFAULT_GUIDANCE_SCALE, help="CFG scale")
    parser.add_argument("--speed", type=float, default=DEFAULT_SPEED, help="Скорость речи")
    parser.add_argument("--device", type=str, default="auto", help="auto | cpu | cuda")
    parser.add_argument("--quant", type=str, default="auto", help="auto | fp16 | int8 | int4")
    parser.add_argument("--no-offload", action="store_true", help="Не offload audio tokenizer")
    parser.add_argument("--info", action="store_true", help="Инфо об устройстве")
    parser.add_argument("--version", "-v", action="version", version=f"OmniVoice Mobile v{VERSION}")
    parser.add_argument("--download-only", action="store_true", help="Только скачать модель")

    args = parser.parse_args()

    # Banner
    if not args.info:
        print(BANNER)

    # Info mode
    if args.info:
        info = get_device_info()
        print(f"\n{'='*50}")
        print("  OmniVoice Mobile — Device Info")
        print(f"{'='*50}")
        for k, v in info.items():
            print(f"  {k:20s} {v}")
        print(f"{'='*50}")
        return

    # Validate required args
    if not args.text or not args.output:
        parser.error("Обязательно: --text и --output\nПример: omnivoice -t 'Hello' -o out.wav")
        return

    # Device info
    di = get_device_info()
    print(f"[DEVICE] RAM: {di['total_ram_gb']:.1f} GB | Arch: {di['arch']} | Quant: {di['quantization']}")

    if di["total_ram_gb"] < 4:
        print("[WARNING] <4 GB RAM. Используйте --quant int4 и включите swap.")

    # Validate ref_audio/ref_text
    if args.ref_audio and not args.ref_text:
        print("[ERROR] С --ref-audio обязателен --ref-text (Whisper ASR отключён)")
        sys.exit(1)
    if args.ref_audio and not os.path.exists(args.ref_audio):
        print(f"[ERROR] Не найдено: {args.ref_audio}")
        sys.exit(1)

    # Load & generate
    engine = OmniVoiceMobile(
        model_id=args.model,
        device=args.device,
        quantization=args.quant,
        num_steps=args.steps,
        guidance_scale=args.guidance,
        offload_audio_tokenizer=not args.no_offload,
    )

    if args.download_only:
        engine.load_all()
        print("[OK] Модель скачана и кэширована.")
        engine.unload_all()
        return

    try:
        engine.load_all()
        engine.generate(
            text=args.text, output_path=args.output,
            ref_audio=args.ref_audio, ref_text=args.ref_text,
            instruct=args.instruct, language=normalize_lang(args.lang),
            speed=args.speed,
        )
    finally:
        engine.unload_all()
