# Wiki Log

新的在上面。格式見 CLAUDE.md。

## 2026-11-24 ingest PaletteWallAndroid（首次）
- 來源：raw/PaletteWallAndroid（commit c539854，2026-09-11）
- 新增：projects/PaletteWallAndroid/overview、architecture、api、data-model、plans、team；modules/diy-live-wallpaper、monetization、retention-and-trial、home-and-browsing、notifications-and-workers（共 11 頁、約 2000 行）
- 更新：index
- 方法：依 raw/SOURCES.md 整理成架構、模組、API、資料模型、決策脈絡；未逐檔翻譯。4 個平行分工各寫一組頁，之後統一檢查 frontmatter、wikilink、安全掃描（無 key / token / host / 帳號）。
- 備註：
  - home-and-browsing 的 confidence 為 medium（FullscreenScreen、LikeCollectionScreen、HomeViewModel 以結構掃描為主，細節可再補讀）。
  - 各頁共約 34 處「待確認」，多為「後端欄位是否已上線」「文件與程式碼不一致」類，集中在 plans（14）與 api / data-model / retention。下次 lint 或拿到後端 repo 時優先處理。
  - 來源文件與程式碼的已知矛盾：remote_template_architecture.md 進度表疑似過時；「Delete Template 尚未實作」但 API 已有 deleteLiveItem；AIScreen 與 FilterScreen 疑為殘留。
  - 後端 repo（scripts 註解提到 web/online-store/backend）不在本來源內，是否納入 wiki 待決定。
