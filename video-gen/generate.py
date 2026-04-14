#!/usr/bin/env python3
"""
最低成本視頻生成器
依賴：pip install gtts pillow moviepy
"""

import os
import sys
import textwrap
from pathlib import Path

# ── 設定 ──────────────────────────────────────────────
FONT_SIZE   = 40
BG_COLOR    = (15, 15, 30)       # 深藍黑底
TEXT_COLOR  = (240, 240, 240)    # 白字
WIDTH, HEIGHT = 1280, 720
FPS         = 24
LANG        = "zh-TW"            # TTS 語言（改 "zh" 用大陸普通話）
OUTPUT_FILE = "output.mp4"
# ─────────────────────────────────────────────────────


def make_frame(text: str, duration: float):
    """返回一個 ImageClip（靜態背景 + 字幕）"""
    from PIL import Image, ImageDraw, ImageFont
    from moviepy.editor import ImageClip

    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 嘗試載入系統字型，失敗用預設
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", FONT_SIZE)
    except Exception:
        font = ImageFont.load_default()

    # 自動換行
    lines = []
    for para in text.split("\n"):
        lines += textwrap.wrap(para, width=28) or [""]

    line_h = FONT_SIZE + 12
    total_h = len(lines) * line_h
    y = (HEIGHT - total_h) // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((WIDTH - w) // 2, y), line, font=font, fill=TEXT_COLOR)
        y += line_h

    return ImageClip(img).set_duration(duration)


def tts(text: str, path: str):
    """用 gTTS 生成語音，返回實際時長"""
    from gtts import gTTS
    from moviepy.editor import AudioFileClip

    gTTS(text=text, lang=LANG).save(path)
    clip = AudioFileClip(path)
    dur = clip.duration
    clip.close()
    return dur


def build_video(script: list[dict]):
    """
    script 格式：
      [{"text": "你好", "tts": True}, ...]
      tts=False → 靜默 2 秒
    """
    from moviepy.editor import concatenate_videoclips, AudioFileClip

    clips = []
    tmp_dir = Path("_tmp_audio")
    tmp_dir.mkdir(exist_ok=True)

    for i, seg in enumerate(script):
        text = seg["text"]
        use_tts = seg.get("tts", True)

        if use_tts:
            audio_path = str(tmp_dir / f"seg_{i}.mp3")
            duration = tts(text, audio_path)
            video = make_frame(text, duration)
            audio = AudioFileClip(audio_path)
            video = video.set_audio(audio)
        else:
            duration = seg.get("duration", 2.0)
            video = make_frame(text, duration)

        clips.append(video)
        print(f"  ✓ 段落 {i+1}/{len(script)}: {text[:20]}… ({duration:.1f}s)")

    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(OUTPUT_FILE, fps=FPS, codec="libx264", audio_codec="aac")
    print(f"\n✅ 完成：{OUTPUT_FILE}")

    # 清理臨時音頻
    for f in tmp_dir.glob("*.mp3"):
        f.unlink()
    tmp_dir.rmdir()


# ── 示範腳本（改呢度就得） ────────────────────────────
DEMO_SCRIPT = [
    {"text": "你好，歡迎嚟到 Ko仔 AI 語言課堂", "tts": True},
    {"text": "今日我哋學習\n日常問候用語",        "tts": True},
    {"text": "第一句：おはようございます\n早晨好",  "tts": True},
    {"text": "第二句：ありがとう\n唔該",           "tts": True},
    {"text": "下次見！",                           "tts": True},
]
# ─────────────────────────────────────────────────────


if __name__ == "__main__":
    # 用法：python generate.py          → 跑示範腳本
    #       python generate.py my.py    → 從外部腳本匯入 SCRIPT 變量
    if len(sys.argv) > 1:
        import importlib.util
        spec = importlib.util.spec_from_file_location("custom", sys.argv[1])
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        script = mod.SCRIPT
    else:
        script = DEMO_SCRIPT

    print(f"▶ 開始生成 {len(script)} 個段落…\n")
    build_video(script)
