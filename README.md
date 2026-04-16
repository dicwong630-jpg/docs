# Mintlify Starter Kit

Use the starter kit to get your docs deployed and ready to customize.

Click the green **Use this template** button at the top of this repo to copy the Mintlify starter kit. The starter kit contains examples with

- Guide pages
- Navigation
- Customizations
- API reference pages
- Use of popular components

**[Follow the full quickstart guide](https://starter.mintlify.com/quickstart)**

## AI-assisted writing

Set up your AI coding tool to work with Mintlify:

```bash
npx skills add https://mintlify.com/docs
```

This command installs Mintlify's documentation skill for your configured AI tools like Claude Code, Cursor, Windsurf, and others. The skill includes component reference, writing standards, and workflow guidance.

See the [AI tools guides](/ai-tools) for tool-specific setup.

## Development

Install the [Mintlify CLI](https://www.npmjs.com/package/mint) to preview your documentation changes locally. To install, use the following command:

```
npm i -g mint
```

Run the following command at the root of your documentation, where your `docs.json` is located:

```
mint dev
```

View your local preview at `http://localhost:3000`.

## Publishing changes

Install our GitHub app from your [dashboard](https://dashboard.mintlify.com/settings/organization/github-app) to propagate changes from your repo to your deployment. Changes are deployed to production automatically after pushing to the default branch.

## 🦞 龍蝦搬運工 (Lobster Porter) 1.0

`lobster_porter` 是一個純 Python（無需外部依賴）批量檔案管理套件，
支援複製、移動、刪除、重命名、分類，並內建撤銷、操作日誌匯出與插件系統。

---

### 功能模組一覽

#### ✅ 已完成的核心模組

| 模組 / 功能 | 檔案 | 說明 |
|---|---|---|
| 批量複製（batch_copy） | `lobster_porter/operations.py` | 保留目錄層級結構 |
| 批量移動（batch_move） | `lobster_porter/operations.py` | 保留目錄層級結構 |
| 批量刪除（batch_delete） | `lobster_porter/operations.py` | 支援 dry_run 預覽 |
| 批量重命名（batch_rename） | `lobster_porter/operations.py` | 正規表達式替換 |
| 撤銷（undo） | `lobster_porter/operations.py` | 撤銷 move/rename；copy/delete 不可撤銷 |
| 操作日誌（OperationLog） | `lobster_porter/operations.py` | 每次操作自動記錄 |
| 日誌匯出（export_log） | `lobster_porter/operations.py` | 支援 JSON 與 CSV |
| Dry Run 模式 | 所有操作 | 模擬執行，不修改任何檔案 |
| Porter 協調器 | `lobster_porter/core.py` | 基於策略的目錄分類搬運 |
| 策略：FlatStrategy | `lobster_porter/strategies.py` | 平鋪至目標根目錄 |
| 策略：ExtensionStrategy | `lobster_porter/strategies.py` | 依副檔名分類 |
| 策略：DateStrategy | `lobster_porter/strategies.py` | 依最後修改日期分類（YYYY/MM）|
| 策略：SizeStrategy | `lobster_porter/strategies.py` | 依檔案大小分類（small/medium/large）|
| 策略：RegexStrategy | `lobster_porter/strategies.py` | 依正規表達式分類 |
| 策略：UserRuleStrategy | `lobster_porter/strategies.py` | 從 JSON 設定檔載入使用者自定義規則 |
| 策略：TypeGroupStrategy | `lobster_porter/strategies.py` | 按廣義類型分類（文件/圖片/音訊/視訊/程式碼/壓縮檔）|
| 策略：CompositeStrategy | `lobster_porter/strategies.py` | 串聯多個策略（首選優先或合併路徑）|
| 插件基礎類別（BasePlugin） | `lobster_porter/plugins/base.py` | 生命週期鉤子 ABC |
| 插件：LoggingPlugin | `lobster_porter/plugins/examples.py` | 詳細操作日誌 |
| 插件：SummaryPlugin | `lobster_porter/plugins/examples.py` | 完成後摘要報告 |
| 插件：FileCounterPlugin | `lobster_porter/plugins/examples.py` | 按副檔名統計數量 |
| 插件：ErrorCollectorPlugin | `lobster_porter/plugins/examples.py` | 收集所有失敗操作 |
| 插件：ProgressBarPlugin | `lobster_porter/plugins/examples.py` | 終端機進度條（無需外部套件）|
| 完整 CLI | `lobster_porter/cli.py` | copy/move/delete/rename/sort/log 子命令 |
| 包裝設定 | `pyproject.toml` | pip install 支援，console_scripts 入口點 |
| 單元測試 | `tests/` | 95 個測試，覆蓋所有核心模組 |

---

### 快速開始

**Python API**

```python
from lobster_porter import LobsterPorter

porter = LobsterPorter()

# 批量複製
porter.batch_copy(
    sources=["/src/a.txt", "/src/sub/b.txt"],
    dest_dir="/dst/",
    base_src="/src/",
)

# 批量移動
porter.batch_move(["/inbox/file.pdf"], "/archive/", base_src="/inbox/")

# 批量刪除（建議先 dry_run=True 確認）
porter.batch_delete(["/tmp/old.txt"])

# 批量重命名（正規表達式）
porter.batch_rename(
    sources=["/docs/report_2023.txt"],
    pattern=r"report_(\d+)\.txt",
    replacement=r"annual_\1.txt",
)

# 撤銷所有 move/rename 操作
porter.undo()

# 匯出操作日誌
porter.export_log("/var/log/porter.json")          # JSON
porter.export_log("/var/log/porter.csv", fmt="csv")  # CSV
```

**使用策略分類搬運整個目錄**

```python
from lobster_porter import Porter
from lobster_porter.strategies import TypeGroupStrategy

porter = Porter(
    src="./inbox",
    dest="./organised",
    strategy=TypeGroupStrategy(),   # 文件/圖片/音訊/視訊/程式碼/壓縮檔
    copy=True,                      # 複製而非移動
    plugins=[SummaryPlugin()],
)
porter.run()
```

**使用者自定義規則（JSON 設定檔）**

```json
{
    "default": "other",
    "rules": [
        {"pattern": "\\.pdf$",   "category": "pdf_docs"},
        {"pattern": "\\.docx?$", "category": "word_docs"},
        {"pattern": "^invoice_", "category": "invoices"}
    ]
}
```

```python
from lobster_porter import Porter
from lobster_porter.strategies import UserRuleStrategy

porter = Porter(
    src="./inbox",
    dest="./organised",
    strategy=UserRuleStrategy("/home/user/.lobster_rules.json"),
)
porter.run()
```

---

### CLI 使用指南

```bash
# 安裝
pip install -e .

# 批量複製（保留層級）
python -m lobster_porter copy /src/docs /src/images --dest /tmp/backup --base /src/

# 批量移動（dry-run 預覽）
python -m lobster_porter move /src/docs --dest /tmp/archive --base /src/ --dry-run

# 批量刪除（必須 --force 或互動確認；建議先 --dry-run）
python -m lobster_porter delete /tmp/old/*.txt --dry-run
python -m lobster_porter delete /tmp/old/*.txt --force

# 批量重命名（正規表達式）
python -m lobster_porter rename /docs/ --pattern "report_(\d+)\.txt" --replacement "annual_\1.txt"

# 依副檔名分類搬運整個目錄
python -m lobster_porter sort /inbox/ --dest /organised/ --strategy extension

# 依廣義類型分類（文件/圖片/程式碼等）
python -m lobster_porter sort /inbox/ --dest /organised/ --strategy typegroup

# 使用自定義規則 JSON
python -m lobster_porter sort /inbox/ --dest /organised/ --strategy user --rules ~/.lobster_rules.json

# 使用正規表達式規則
python -m lobster_porter sort /inbox/ --dest /organised/ --strategy regex \
    --regex-rules "^invoice:bills" "\.pdf$:pdfs" --copy

# 只處理指定格式（include filter）
python -m lobster_porter sort /inbox/ --dest /organised/ --include "*.pdf" "*.docx"

# 匯出操作日誌
python -m lobster_porter sort /inbox/ --dest /organised/ --log-out /var/log/porter.json

# 查看日誌檔
python -m lobster_porter log /var/log/porter.json
python -m lobster_porter log /var/log/porter.json --filter-failed
python -m lobster_porter log /var/log/porter.json --export /var/log/porter.csv
```

---

### 套件目錄結構

```
lobster_porter/
├── __init__.py          # 公開 API（Porter、LobsterPorter、OperationLog、collect_files）
├── __main__.py          # python -m lobster_porter 入口點
├── core.py              # Porter 協調器（策略+插件+干跑+include/exclude）
├── operations.py        # LobsterPorter 批量操作（copy/move/delete/rename/undo/export）
├── strategies.py        # 內建策略（Flat/Extension/Date/Size/Regex/UserRule/TypeGroup/Composite）
├── cli.py               # 完整 CLI（copy/move/delete/rename/sort/log）
└── plugins/
    ├── __init__.py      # 插件子套件 API
    ├── base.py          # BasePlugin 抽象類別（生命週期鉤子）
    └── examples.py      # 示範插件（Logging/Summary/FileCounter/ErrorCollector/ProgressBar）
tests/
├── test_core.py         # Porter 核心測試（35 個）
├── test_operations.py   # 批量操作測試（34 個）
├── test_strategies.py   # 策略測試（26 個）
└── test_cli.py          # CLI 測試（25 個）
pyproject.toml           # 套件設定（pip install 支援）
```

---

### 執行測試

```bash
python -m unittest discover -s tests -v
```

---

## Need help?

### Troubleshooting

- If your dev environment isn't running: Run `mint update` to ensure you have the most recent version of the CLI.
- If a page loads as a 404: Make sure you are running in a folder with a valid `docs.json`.

### Resources
- [Mintlify documentation](https://mintlify.com/docs)
