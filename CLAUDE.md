# wiki-LLM-PaletteWall — Claude Code 規範

這是一個 **LLM 維護的知識 wiki**。`raw/` 放原始來源（唯讀、不入 git），`wiki/` 是 LLM 從來源整理出的知識頁（入 git）。
人類幾乎不直接寫 wiki 頁；人類提供來源、提問、下指令，LLM 負責讀寫與維護。

## 三種工作流程

### 1. ingest（吸收來源 → 寫 wiki）
1. 先讀 `raw/SOURCES.md`，確認該來源的類型、要怎麼整理、哪些路徑要忽略、哪些內容**絕不能摘錄**。
2. 讀來源。程式碼來源**不要逐檔翻譯**，要整理成架構、模組職責、API、資料模型、決策脈絡。
3. 寫入 `wiki/<分類>/<來源名>/...`（見下方目錄規範）。已有頁面就更新，不要另開重複頁。
4. 更新 `wiki/index.md`（新頁加一行，改頁更新摘要）。
5. 在 `wiki/log.md` **最上方**追加一筆紀錄。

### 2. query（回答問題）
1. 先讀 `wiki/index.md` 找相關頁，再讀那些頁回答。
2. wiki 沒有答案時才去翻 `raw/`，並在回答裡註明「來自 raw，尚未寫進 wiki」。
3. 若 raw 翻出有價值的新知識，順手補進 wiki（依 ingest 流程步驟 3–5）。

### 3. lint（健檢）
檢查並修正：壞掉的 `[[wikilink]]`、index.md 漏列或多列的頁、互相矛盾的敘述、來源已更新但 wiki 過時的頁、frontmatter 缺欄位。
每次 lint 也要在 `wiki/log.md` 記一筆。

## 目錄規範

```
wiki/
  index.md                 所有頁面的目錄，每頁一行：- [[路徑]] — 一句話摘要
  log.md                   操作日誌，新的在上面
  projects/<來源名>/       某個專案（程式碼來源）的知識
    overview.md            產品定位、技術棧、入口點
    architecture.md        分層、資料流、DI、導航
    api.md                 對外 API 端點、驗證方式
    data-model.md          本地資料庫 table 與關聯、SharedPrefs、遠端 DTO
    modules/<模組>.md      功能模組（一個功能一頁）
    plans.md               規劃與決策文件摘要
    team.md                團隊/成長/營運資料摘要
  concepts/                跨專案的概念或術語（需要時才建）
  decisions/               跨專案的重要決策（需要時才建）
```

## 頁面格式

每頁開頭必須有 frontmatter：

```markdown
---
title: 頁面標題
source: raw/PaletteWallAndroid/app/src/main/java/.../data/remote   # 主要依據的來源路徑，可多個
updated: 2026-11-24
confidence: high | medium | low    # 對內容正確性的把握；推測的東西標 low
---
```

內文規則：
- 用 `[[projects/PaletteWallAndroid/api]]` 這種**相對 wiki/ 的路徑**互連，不加 `.md`。
- 從來源引用具體檔案時寫相對來源根目錄的路徑，例如 `app/src/main/java/com/palettex/palettewall/service/DiyLiveWallpaperService.kt`。
- 事實與推測分開：推測句要寫「推測：」或「待確認：」。
- 寫「是什麼、為什麼、怎麼接」；不要貼大段程式碼，必要時貼 10 行以內的關鍵片段。
- 語言：繁體中文為主，專有名詞、類別名、檔名保留英文。

## 安全規則（永遠適用）

- **絕不**把 `.env`、`google-services.json`、config/secrets、任何 API key、token、連線字串、密碼寫進 wiki。
  可以寫「驗證用 x-app-key header」，不能寫 key 的值。
- `raw/` 底下的來源 repo 不入 git（見 `.gitignore`），wiki 頁只放整理後的知識。

## log.md 紀錄格式

```markdown
## 2026-11-24 ingest PaletteWallAndroid
- 來源：raw/PaletteWallAndroid（commit abc1234）
- 新增：projects/PaletteWallAndroid/overview, architecture, ...
- 更新：index
- 備註：...
```
