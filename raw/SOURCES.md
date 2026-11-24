# Raw Sources

ingest 前先讀這份；每個來源一節。

## PaletteWallAndroid/

- What it is: Android 桌布 App「PaletteWall」(package `com.palettex.palettewall`)，靜態桌布 + DIY Live Wallpaper，含付費/廣告/花朵試用系統。Kotlin、Jetpack Compose、Clean Architecture、Hilt、Room、Retrofit、Firebase。
- Type: source code（git clone，含內部規劃文件與團隊資料）
- How to ingest: summarize into architecture, module responsibilities, API endpoints, and table relationships; do not translate file by file
- Key paths:
  - `README.md`、`CLAUDE.md` — 產品與工程規則總覽（CLAUDE.md 的 Critical Rules 很重要）
  - `app/src/main/java/com/palettex/palettewall/` — 程式碼，分 `data/`、`domain/`、`ui/`、`service/`、`di/`、`util/`
  - `app/src/main/AndroidManifest.xml`、`app/build.gradle.kts` — 入口點、權限、build variants、依賴
  - `doc/` — 規劃與設計文件（`doc/diy/` 是 DIY 子系統的設計文件）
  - `team/` — 成長/營運：`TEAM_BRIEF.md`、`growth/`、`reports/`
  - `scripts/` — 輔助工具（DIY template 上傳、定價）
- Ignore: `build/`、`.gradle/`、`gradle/`、`gradlew*`、`app/src/main/res/`、`app/src/main/assets/cached_images/`、`app/src/androidTest/`、`app/src/test/`、`team/reports/raw/*.csv`（可用 reports 的 md 摘要代替）
- Never excerpt: `.env`、`app/google-services.json`、`local.properties`、config/secrets、任何 key、token、連線字串
- Wiki location: wiki/projects/PaletteWallAndroid/
