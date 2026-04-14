# 最低成本視頻生成器

純 Python，**零 API 費用**。

## 安裝依賴

```bash
pip install gtts pillow moviepy
```

> macOS 可能需要：`brew install ffmpeg`  
> Ubuntu：`sudo apt install ffmpeg`

## 使用方法

### 方法一：直接跑示範

```bash
cd video-gen
python generate.py
# 輸出：output.mp4
```

### 方法二：自訂腳本

新建一個 `my_script.py`：

```python
SCRIPT = [
    {"text": "第一段文字，會自動生成語音", "tts": True},
    {"text": "第二段，靜音 3 秒",          "tts": False, "duration": 3.0},
    {"text": "第三段繼續",                  "tts": True},
]
```

然後執行：

```bash
python generate.py my_script.py
```

## 設定

喺 `generate.py` 頂部改：

| 變量 | 預設 | 說明 |
|------|------|------|
| `LANG` | `"zh-TW"` | TTS 語言（`"zh"` = 普通話，`"ja"` = 日文）|
| `BG_COLOR` | 深藍黑 | RGB tuple |
| `TEXT_COLOR` | 白色 | RGB tuple |
| `WIDTH / HEIGHT` | 1280×720 | 解析度 |
| `FPS` | 24 | 幀率 |
| `OUTPUT_FILE` | `output.mp4` | 輸出文件名 |

## 費用

| 工具 | 費用 |
|------|------|
| gTTS（Google TTS） | 免費（網絡請求）|
| Pillow | 免費 |
| MoviePy + ffmpeg | 免費 |
| **合計** | **$0** |
