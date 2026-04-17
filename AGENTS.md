# 文件專案說明

## ⚡ 給 AI 的快速提示（每次 session 必讀）

此 repo 是一個以**繁體中文**撰寫的 Mintlify 文件站，主題為「AI 自動化影音製作」。
所有頁面、導覽、設定均已翻譯為繁體中文。

### 已完成的工作
- [x] `docs.json` — 站名、所有導覽標籤、群組、錨點全部翻譯為繁體中文
- [x] `assets/custom.css` — 加入 Noto Sans TC 字型，CJK 行距與字距優化
- [x] `index.mdx` — 首頁翻譯完成
- [x] `quickstart.mdx` — 快速入門翻譯完成
- [x] `development.mdx` — 本機開發翻譯完成
- [x] `essentials/settings.mdx` — 全域設定翻譯完成
- [x] `essentials/navigation.mdx` — 導覽結構翻譯完成
- [x] `essentials/markdown.mdx` — Markdown 語法翻譯完成
- [x] `essentials/code.mdx` — 程式碼區塊翻譯完成
- [x] `essentials/images.mdx` — 圖片與嵌入內容翻譯完成
- [x] `essentials/reusable-snippets.mdx` — 可重複使用的片段翻譯完成
- [x] `ai-tools/cursor.mdx` — Cursor 設定翻譯完成
- [x] `ai-tools/claude-code.mdx` — Claude Code 設定翻譯完成
- [x] `ai-tools/windsurf.mdx` — Windsurf 設定翻譯完成
- [x] `api-reference/introduction.mdx` — API 簡介翻譯完成
- [x] `AGENTS.md` — 本檔案，繁中專案說明

### 待辦事項
- [ ] `api-reference/endpoint/` 下的端點頁面（get / create / delete / webhook）— 確認翻譯狀態
- [ ] `snippets/snippet-intro.mdx` — 確認翻譯狀態
- [ ] 用 `mint broken-links` 檢查所有連結是否正常
- [ ] 考慮替換 logo、favicon 為專案專屬圖示

---

## 關於本專案

- 本文件網站基於 [Mintlify](https://mintlify.com) 建置
- 頁面為帶有 YAML frontmatter 的 MDX 檔案
- 配置檔位於 `docs.json`
- 執行 `mint dev` 在本機預覽
- 執行 `mint broken-links` 檢查連結
- 所有文件內容以**繁體中文**撰寫
- 字型使用 Noto Sans TC（設定於 `assets/custom.css`）

## 術語規範

- 使用「文件」而非「docs」
- 使用「元件」而非「component」
- 使用「側邊欄」而非「sidebar」
- 使用「導覽」而非「navigation」
- 使用「管理後台」而非「dashboard」

## 樣式偏好

- 使用主動語氣和第二人稱（「你」）
- 句子保持簡潔——每句一個概念
- 標題使用句子大小寫
- UI 元素使用粗體：點擊**設定**
- 檔名、指令、路徑和程式碼引用使用程式碼格式
- 標點符號使用全形中文標點（。，、：；！？）
- 中英文之間保留適當空格

## 內容範圍

- 文件內容以繁體中文為主
- 技術術語可保留英文原文並於括號內附上中文說明
- 程式碼區塊和指令維持英文原文
