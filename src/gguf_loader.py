#!/usr/bin/env python3
"""
OmniVoice Mobile — Модуль для загрузки квантованной модели через GGUF/llama.cpp.

Для Termux: скомпилируйте llama.cpp с поддержкой ARM64 NEON.

Этот модуль позволяет использовать INT4/INT8 квантизированную версию
Qwen3-0.6B backbone через llama.cpp Python binding, что значительно
снижает потребление памяти и ускоряет инференс на ARM64 CPU.
"""

import os
import sys
import struct
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple


class GGUFLoader:
    """Загрузчик GGUF файлов для инференса через llama.cpp."""

    def __init__(self, gguf_path: str):
        self.gguf_path = gguf_path
        self._model = None
        self._ctx = None
        self._llama = None

    def _init_llama_cpp(self):
        """Инициализирует llama.cpp binding."""
        try:
            from llama_cpp import Llama
            self._llama = Llama
            return True
        except ImportError:
            pass

        # Пробуем установленный llama-cpp-python
        try:
            import llama_cpp
            self._llama = llama_cpp.Llama
            return True
        except ImportError:
            pass

        return False

    def load(self, n_ctx: int = 4096, n_threads: int = 0):
        """
        Загружает GGUF модель в память.

        Args:
            n_ctx: Размер контекста
            n_threads: Число потоков (0 = auto)
        """
        if not self._init_llama_cpp():
            raise RuntimeError(
                "llama-cpp-python не установлен.\n"
                "Установка: CMAKE_ARGS='-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS' "
                "pip install llama-cpp-python\n"
                "Или для Termux: pip install llama-cpp-python --no-cache-dir"
            )

        if n_threads == 0:
            import os
            n_threads = os.cpu_count() or 4

        print(f"  Загрузка GGUF: {self.gguf_path}")
        print(f"  Threads: {n_threads}, Context: {n_ctx}")

        self._model = self._llama(
            model_path=self.gguf_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_batch=512,
            verbose=False,
        )

        return self._model

    def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.6,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
    ) -> str:
        """Генерирует текст через llama.cpp."""
        if self._model is None:
            raise RuntimeError("Модель не загружена. Вызовите load() сначала.")

        output = self._model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop or [],
            echo=False,
        )

        return output["choices"][0]["text"]

    def unload(self):
        """Выгружает модель из памяти."""
        if self._model is not None:
            del self._model
            self._model = None

        import gc
        gc.collect()
        print("  GGUF модель выгружена из памяти")


def parse_gguf_metadata(gguf_path: str) -> Dict[str, Any]:
    """Читает метаданные из GGUF файла без загрузки модели."""
    metadata = {}

    try:
        with open(gguf_path, 'rb') as f:
            # GGUF magic: "GGUF" в hex = 0x46554747
            magic = f.read(4)
            if magic != b'GGUF':
                raise ValueError(f"Не GGUF файл: {gguf_path}")

            version = struct.unpack('<I', f.read(4))[0]
            tensor_count = struct.unpack('<Q', f.read(8))[0]
            metadata_kv_count = struct.unpack('<Q', f.read(8))[0]

            metadata["gguf_version"] = version
            metadata["tensor_count"] = tensor_count
            metadata["metadata_kv_count"] = metadata_kv_count

            # Читаем metadata key-value пары
            for _ in range(min(metadata_kv_count, 50)):  # лимит
                # Key
                key_len = struct.unpack('<Q', f.read(8))[0]
                key = f.read(key_len).decode('utf-8')

                # Value type
                value_type = struct.unpack('<I', f.read(4))[0]

                # GGUF types
                if value_type == 8:  # STRING
                    str_len = struct.unpack('<Q', f.read(8))[0]
                    value = f.read(str_len).decode('utf-8')
                elif value_type == 4:  # UINT32
                    value = struct.unpack('<I', f.read(4))[0]
                elif value_type == 6:  # INT32
                    value = struct.unpack('<i', f.read(4))[0]
                elif value_type == 9:  # ARRAY of STRING
                    arr_len = struct.unpack('<Q', f.read(8))[0]
                    arr_type = struct.unpack('<I', f.read(4))[0]
                    value = []
                    for _ in range(min(arr_len, 20)):
                        s_len = struct.unpack('<Q', f.read(8))[0]
                        value.append(f.read(s_len).decode('utf-8'))
                    value = value[:5]  # первые 5
                else:
                    # Skip unknown types
                    break

                metadata[key] = value

    except Exception as e:
        print(f"  [WARNING] Ошибка чтения GGUF: {e}")

    return metadata


def estimate_memory_requirements(gguf_path: str) -> Dict[str, float]:
    """Оценивает требования к памяти для GGUF модели."""
    file_size = os.path.getsize(gguf_path)

    # GGUF модели обычно загружаются целиком + overhead
    base_mem = file_size * 1.3 / (1024**3)  # ~30% overhead

    # KV cache estimation ( зависит от контекста )
    kv_cache_gb = 0.5  # приблизительно для 4K контекста

    # Total
    total_gb = base_mem + kv_cache_gb

    return {
        "model_file_gb": file_size / (1024**3),
        "estimated_ram_gb": round(total_gb, 2),
        "min_ram_gb": round(total_gb * 0.8, 2),
        "recommended_ram_gb": round(total_gb * 1.2, 2),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GGUF утилиты для OmniVoice Mobile")
    parser.add_argument("--file", "-f", type=str, help="Путь к GGUF файлу")
    parser.add_argument("--info", action="store_true", help="Показать метаданные")
    parser.add_argument("--memory", action="store_true", help="Оценить требования к памяти")
    args = parser.parse_args()

    if args.file:
        if args.info:
            meta = parse_gguf_metadata(args.file)
            print(json.dumps(meta, indent=2, ensure_ascii=False))
        if args.memory:
            mem = estimate_memory_requirements(args.file)
            print(json.dumps(mem, indent=2))
    else:
        print("Использование: python gguf_loader.py -f model.gguf --info --memory")
