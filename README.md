# AI 自動化影音製作文件

使用本入門套件，快速部署並自訂你的繁體中文文件網站。

點擊儲存庫頂部的綠色 **Use this template** 按鈕，複製本 Mintlify 入門套件。套件包含以下範例：

- 指南頁面
- 導覽結構
- 自訂設定
- API 參考頁面
- 常用元件使用方式

**[查看完整快速入門指南](https://starter.mintlify.com/quickstart)**

## AI 輔助撰寫

設定你的 AI 編碼工具以搭配 Mintlify 使用：

```bash
npx skills add https://mintlify.com/docs
```

此指令會為你設定的 AI 工具（如 Claude Code、Cursor、Windsurf 等）安裝 Mintlify 的文件技能，包含元件參考、撰寫標準和工作流程指引。

詳細工具設定請參閱 [AI 工具指南](/ai-tools)。

## 本機開發

安裝 [Mintlify CLI](https://www.npmjs.com/package/mint)，在本機預覽文件變更。使用以下指令安裝：

```
npm i -g mint
```

在包含 `docs.json` 的文件根目錄執行以下指令：

```
mint dev
```

在 `http://localhost:3000` 查看本機預覽。

## 發布變更

從 [管理後台](https://dashboard.mintlify.com/settings/organization/github-app) 安裝我們的 GitHub 應用程式，將儲存庫的變更同步到部署環境。推送到預設分支後，變更將自動部署到正式環境。

## 繁體中文排版

本專案已預設啟用繁體中文排版最佳化：

- **字型**：Noto Sans TC（Google Fonts）
- **行高**：1.9（提升中文閱讀舒適度）
- **字距**：適當調整，符合中文閱讀習慣
- **標題字重**：700，確保清晰層次感

自訂 CSS 樣式位於 `assets/custom.css`。

## 需要協助？

### 疑難排解

- 若開發環境無法啟動：執行 `mint update` 確保使用最新版 CLI。
- 若頁面顯示 404：確認你在包含有效 `docs.json` 的資料夾中執行。

### 參考資源
- [Mintlify 官方文件](https://mintlify.com/docs)
