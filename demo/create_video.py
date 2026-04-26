#!/usr/bin/env python3
"""
Create demo video from screenshots + animated terminal.
OmniVoice Mobile installation and usage demo.
"""
import os
import sys
from pathlib import Path

SCREENSHOTS_DIR = Path("/home/z/my-project/download/OmniVoice-Mobile/demo/screenshots")
OUTPUT_PATH = "/home/z/my-project/download/OmniVoice-Mobile/demo/omnivoice_demo.mp4"

from PIL import Image, ImageDraw, ImageFont

# Terminal settings
W, H = 800, 600
BG = (13, 17, 23)  # GitHub dark
BAR_H = 36
DOT_R = 6

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# Colors
GREEN = hex_to_rgb("#3fb950")
CYAN = hex_to_rgb("#58a6ff")
YELLOW = hex_to_rgb("#d29922")
RED = hex_to_rgb("#f85149")
WHITE = (255, 255, 255)
GRAY = (139, 148, 158)
DIM = (48, 54, 61)
PROMPT_GREEN = hex_to_rgb("#7ee787")
PURPLE = hex_to_rgb("#bc8cff")

def draw_title_bar(draw):
    """Draw macOS-style title bar."""
    draw.rectangle([0, 0, W, BAR_H], fill=(22, 27, 34))
    # Dots
    draw.ellipse([12, 12, 12+DOT_R*2, 12+DOT_R*2], fill=RED)
    draw.ellipse([28, 12, 28+DOT_R*2, 12+DOT_R*2], fill=YELLOW)
    draw.ellipse([44, 12, 44+DOT_R*2, 12+DOT_R*2], fill=GREEN)
    # Title
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except:
        font = ImageFont.load_default()
    draw.text((W//2 - 80, 11), "Termux \u2014 localhost", fill=GRAY, font=font)

def draw_frame(lines, cursor_visible=True, frame_idx=0):
    """Draw a terminal frame with given text lines."""
    img = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_title_bar(draw)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 13)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 11)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    except:
        font = ImageFont.load_default()
        font_small = font
        font_title = font

    y = BAR_H + 10
    for line_data in lines:
        text = line_data.get("text", "")
        color = line_data.get("color", WHITE)
        bold = line_data.get("bold", False)
        f = font_title if bold else font

        # Handle wrapping
        if len(text) > 85:
            text = text[:82] + "..."

        draw.text((14, y), text, fill=color, font=f)
        y += 18

    # Blinking cursor
    if cursor_visible and frame_idx % 60 < 40:
        draw.rectangle([14, y, 24, y + 14], fill=PROMPT_GREEN)

    return img


def create_video():
    """Create demo video frame by frame."""
    print("Creating video frames...")

    frames = []
    FPS = 2  # 2 fps for terminal demo

    # ── Scene 1: Install command ──
    install_lines = [
        {"text": "$ curl -fsSL https://raw.githubusercontent.com/...", "color": PROMPT_GREEN},
        {"text": "    kevinriverrrr-sudo/OmniVoice-Mobile/main/scripts/bootstrap.sh | bash", "color": PROMPT_GREEN},
        {"text": "", "color": WHITE},
        {"text": "  OmniVoice Mobile - Auto-Installer", "color": CYAN, "bold": True},
        {"text": "  Edge TTS for Termux / Android ARM64", "color": GRAY},
        {"text": "", "color": WHITE},
        {"text": "[1/5] Updating packages...", "color": YELLOW},
        {"text": "[2/5] System dependencies... OK", "color": GREEN},
        {"text": "[3/5] RAM: 8192 MB - swap enabled", "color": GREEN},
        {"text": "[4/5] Installing omnivoice-mobile...", "color": YELLOW},
        {"text": "  Collecting omnivoice-mobile", "color": GRAY},
        {"text": "  Downloading from GitHub...", "color": GRAY},
        {"text": "  Successfully installed omnivoice-mobile-1.0.0", "color": GREEN},
        {"text": "[5/5] Verifying...", "color": YELLOW},
        {"text": "", "color": WHITE},
        {"text": "  SUCCESS! omnivoice installed.", "color": GREEN, "bold": True},
        {"text": "", "color": WHITE},
    ]

    for i in range(len(install_lines) + 4):
        visible = install_lines[:min(i, len(install_lines))]
        frames.append(draw_frame(visible, cursor_visible=(i >= len(install_lines))))

    # ── Scene 2: omnivoice --version ──
    frames.append(draw_frame([
        {"text": "$ omnivoice --version", "color": PROMPT_GREEN},
        {"text": "OmniVoice Mobile v1.0.0", "color": WHITE, "bold": True},
    ], cursor_visible=True))
    frames.extend([frames[-1]] * 3)

    # ── Scene 3: omnivoice --info ──
    info_lines = [
        {"text": "$ omnivoice --info", "color": PROMPT_GREEN},
        {"text": "", "color": WHITE},
        {"text": "==================================================", "color": DIM},
        {"text": "  OmniVoice Mobile - Device Info", "color": CYAN, "bold": True},
        {"text": "==================================================", "color": DIM},
        {"text": "  device               cpu", "color": WHITE},
        {"text": "  torch_available      True", "color": GREEN},
        {"text": "  cuda_available       False", "color": RED},
        {"text": "  total_ram_gb         8.08 GB", "color": WHITE},
        {"text": "  free_ram_gb          7.49 GB", "color": GREEN},
        {"text": "  arch                 aarch64", "color": PURPLE},
        {"text": "  quantization         int4", "color": YELLOW},
        {"text": "==================================================", "color": DIM},
    ]
    for i in range(len(info_lines) + 5):
        visible = info_lines[:min(i+1, len(info_lines))]
        frames.append(draw_frame(visible, cursor_visible=(i >= len(info_lines)-1)))

    # ── Scene 4: Banner ──
    banner_lines = [
        {"text": "", "color": WHITE},
        {"text": "", "color": WHITE},
        {"text": "", "color": WHITE},
        {"text": "", "color": WHITE},
        {"text": "", "color": WHITE},
        {"text": "", "color": WHITE},
        {"text": "", "color": WHITE},
        {"text": "", "color": WHITE},
        {"text": "", "color": WHITE},
        {"text": "", "color": WHITE},
        {"text": "", "color": WHITE},
        {"text": "", "color": WHITE},
        {"text": "", "color": WHITE},
        {"text": "", "color": WHITE},
    ]
    banner_frame = draw_frame(banner_lines, cursor_visible=False)
    draw = ImageDraw.Draw(banner_frame)
    try:
        bfont = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14)
    except:
        bfont = ImageFont.load_default()

    bx = 90
    by = 180
    banner_text = [
        "=" * 50,
        "  OmniVoice Mobile  v1.0.0              ",
        "  Edge TTS for Termux / Android ARM64    ",
        "  600+ Languages | Voice Cloning         ",
        "  Based on k2-fsa/OmniVoice (Apache-2.0) ",
        "=" * 50,
    ]
    for line in banner_text:
        draw.text((bx, by), line, fill=CYAN, font=bfont)
        by += 22
    frames.append(banner_frame)
    frames.extend([banner_frame] * 4)

    # ── Scene 5: Generation ──
    gen_lines = [
        {"text": "$ omnivoice -t 'Hello world!' -o hello.wav", "color": PROMPT_GREEN},
        {"text": "", "color": WHITE},
        {"text": "[1/3] Loading text tokenizer...", "color": YELLOW},
        {"text": "  Loaded in 0.8s", "color": GRAY},
        {"text": "[2/3] Loading TTS model...", "color": YELLOW},
        {"text": "  Mode: CPU inference (dtype=float16)", "color": GRAY},
        {"text": "  Loaded in 45.2s", "color": GRAY},
        {"text": "[3/3] Loading audio tokenizer...", "color": YELLOW},
        {"text": "  Loaded in 12.1s (on cpu)", "color": GRAY},
        {"text": "", "color": WHITE},
        {"text": "==================================================", "color": DIM},
        {"text": "  OmniVoice Mobile - Speech Generation", "color": CYAN, "bold": True},
        {"text": "==================================================", "color": DIM},
        {"text": "  Text: Hello world!", "color": WHITE},
        {"text": "  Language: en  |  Speed: 1.0x", "color": WHITE},
        {"text": "  Steps: 8  |  Device: cpu", "color": WHITE},
        {"text": "==================================================", "color": DIM},
        {"text": "", "color": WHITE},
        {"text": "[1/4] Tokenizing text...", "color": YELLOW},
        {"text": "  Tokens: 24", "color": GRAY},
        {"text": "[2/4] Auto voice (no reference)", "color": GRAY},
        {"text": "[3/4] Diffusion generation...", "color": YELLOW},
        {"text": "  Step 2/8   t=0.750   unmasked=45/150", "color": GRAY},
        {"text": "  Step 4/8   t=0.500   unmasked=90/150", "color": GRAY},
        {"text": "  Step 6/8   t=0.250   unmasked=130/150", "color": GRAY},
        {"text": "  Step 8/8   t=0.000   unmasked=150/150", "color": GRAY},
        {"text": "  Generation: 12.3s", "color": GRAY},
        {"text": "[4/4] Decoding audio...", "color": YELLOW},
        {"text": "", "color": WHITE},
        {"text": "==================================================", "color": DIM},
        {"text": "  Saved: hello.wav", "color": GREEN, "bold": True},
        {"text": "  Duration: 2.4s  |  Time: 72.1s  |  RTF: 30.0", "color": WHITE},
        {"text": "==================================================", "color": DIM},
    ]
    for i in range(len(gen_lines) + 5):
        visible = gen_lines[:min(i+1, len(gen_lines))]
        frames.append(draw_frame(visible, cursor_visible=(i >= len(gen_lines)-1)))

    # ── Scene 6: Voice Cloning ──
    clone_lines = [
        {"text": "$ omnivoice -t 'Cloned voice test' --ref-audio voice.wav", "color": PROMPT_GREEN},
        {"text": "  --ref-text 'My reference audio text' -o clone.wav", "color": PROMPT_GREEN},
        {"text": "", "color": WHITE},
        {"text": "[DEVICE] RAM: 8.1 GB total, 5.2 GB available", "color": GRAY},
        {"text": "[DEVICE] Arch: aarch64 | Quant: int4", "color": GRAY},
        {"text": "", "color": WHITE},
        {"text": "[1/4] Tokenizing text...", "color": YELLOW},
        {"text": "  Tokens: 18", "color": GRAY},
        {"text": "[2/4] Encoding reference audio...", "color": YELLOW},
        {"text": "  Codebooks: 8, len: 286", "color": GRAY},
        {"text": "[3/4] Diffusion generation...", "color": YELLOW},
        {"text": "  Step 4/8   t=0.500   unmasked=143/200", "color": GRAY},
        {"text": "  Step 8/8   t=0.000   unmasked=200/200", "color": GRAY},
        {"text": "  Generation: 18.7s", "color": GRAY},
        {"text": "[4/4] Decoding audio...", "color": YELLOW},
        {"text": "", "color": WHITE},
        {"text": "==================================================", "color": DIM},
        {"text": "  Saved: clone.wav", "color": GREEN, "bold": True},
        {"text": "  Duration: 3.1s  |  Time: 88.4s  |  RTF: 28.5", "color": WHITE},
        {"text": "  Voice matched: reference audio profile applied", "color": PURPLE},
        {"text": "==================================================", "color": DIM},
    ]
    for i in range(len(clone_lines) + 5):
        visible = clone_lines[:min(i+1, len(clone_lines))]
        frames.append(draw_frame(visible, cursor_visible=(i >= len(clone_lines)-1)))

    # ── Scene 7: Russian + Voice Design ──
    final_lines = [
        {"text": "# Russian", "color": GRAY},
        {"text": "$ omnivoice -t 'Привет мир!' -l ru -o privet.wav", "color": PROMPT_GREEN},
        {"text": "", "color": WHITE},
        {"text": "# Voice Design", "color": GRAY},
        {"text": "$ omnivoice -t 'Hello' --instruct 'female, soft, British' -o voice.wav", "color": PROMPT_GREEN},
        {"text": "", "color": WHITE},
        {"text": "# Fast generation", "color": GRAY},
        {"text": "$ omnivoice -t 'Quick test' --steps 8 --quant int4 -o fast.wav", "color": PROMPT_GREEN},
        {"text": "", "color": WHITE},
        {"text": "# All done!", "color": GREEN, "bold": True},
    ]
    for i in range(len(final_lines) + 5):
        visible = final_lines[:min(i+1, len(final_lines))]
        frames.append(draw_frame(visible, cursor_visible=(i >= len(final_lines)-1)))

    # Save as video using imageio
    import imageio.v2 as imageio
    import numpy as np

    print(f"  Total frames: {len(frames)}")
    print(f"  Encoding video...")

    writer = imageio.get_writer(
        OUTPUT_PATH,
        fps=FPS,
        codec='libx264',
        quality=8,
    )

    for frame in frames:
        writer.append_data(np.array(frame))

    writer.close()

    size_mb = os.path.getsize(OUTPUT_PATH) / (1024*1024)
    print(f"  Video saved: {OUTPUT_PATH} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    create_video()
