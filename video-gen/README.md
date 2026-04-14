# 最低成本視頻生成器

純 Python，**零 API 費用**。三步搞掂：

---

## 第一步：安裝（複製落終端機，跑一次就夠）

```bash
pip install gtts pillow moviepy
```

> macOS 需要：`brew install ffmpeg`  
> Ubuntu：`sudo apt install ffmpeg`

---

## 第二步：用中文描繪視頻方向

新建一個 `我的視頻.txt`，每行 = 一個場景，終端機會自動幫每行配音：

```
你好，歡迎嚟到 Ko仔 AI 語言課堂
今日我哋學習日常問候用語
第一句：おはようございます，即係早晨好
第二句：ありがとう，即係唔該
下次見！
```

> 純文字，唔使任何 Python 語法，想寫咩就寫咩。

---

## 第三步：呼喚視頻出嚟

```bash
cd video-gen
python generate.py 我的視頻.txt
```

輸出：`output.mp4` ✅

---

## 唔使 txt 文件？直接試示範

```bash
python generate.py
```

---

## 設定（改 `generate.py` 頂部）

| 變量 | 預設 | 說明 |
|------|------|------|
| `LANG` | `"zh-TW"` | TTS 語言（`"zh"` = 普通話，`"ja"` = 日文，`"en"` = 英文）|
| `BG_COLOR` | 深藍黑 | RGB tuple |
| `TEXT_COLOR` | 白色 | RGB tuple |
| `WIDTH / HEIGHT` | 1280×720 | 解析度 |
| `FPS` | 24 | 幀率 |
| `OUTPUT_FILE` | `output.mp4` | 輸出文件名 |

---

## 費用

| 工具 | 費用 |
|------|------|
| gTTS（Google TTS） | 免費（唔使 API key）|
| Pillow | 免費 |
| MoviePy + ffmpeg | 免費 |
| **合計** | **$0** |
