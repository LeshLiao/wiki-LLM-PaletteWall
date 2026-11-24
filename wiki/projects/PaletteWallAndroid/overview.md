---
title: PaletteWallAndroid 總覽
source:
  - raw/PaletteWallAndroid/README.md
  - raw/PaletteWallAndroid/CLAUDE.md
  - raw/PaletteWallAndroid/doc/instructions.md
  - raw/PaletteWallAndroid/app/build.gradle.kts
  - raw/PaletteWallAndroid/app/src/main/AndroidManifest.xml
  - raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/PaletteWallApplication.kt
  - raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/MainActivity.kt
  - raw/PaletteWallAndroid/team/TEAM_BRIEF.md
  - raw/PaletteWallAndroid/doc/google_play_listing_and_release_note.md
updated: 2026-11-24
confidence: high
---

# PaletteWallAndroid 總覽

## 產品定位

**PaletteWall**（商店顯示名 PaletteX / PaletteWall DIY Live Wallpaper）是一款已上架 Google Play 的 Android 桌布 App，package name `com.palettex.palettewall`。

產品有兩條主線：

| 主線 | 內容 | 狀態 |
|---|---|---|
| **靜態桌布** | 後端精選的 HD 桌布，分 Nature / Abstract / Anime 等 catalog，支援顏色搜尋、關鍵字搜尋、收藏、下載套用 | 原始功能，仍在 App 內（Static 分頁） |
| **DIY Live Wallpaper** | 使用者用**自己的照片**套進後端提供的 template（相框、背景、裝飾、貼紙、文字、動畫），產生會動的動態桌布；由 App 自己的 `WallpaperService` 渲染 | **現在的主力功能**，首頁（Live 分頁）即是它 |

- 商店文案主軸（`doc/google_play_listing_and_release_note.md`）：第一句永遠是「你自己的照片 → 有動畫的動態桌布」，刻意與圖庫型桌布 App 區隔；避開與 Wave 在「live wallpaper maker」關鍵字正面對撞。
- 目標使用者：想把個人照片做成動態桌布的一般手機使用者；商店頁有 9 個語系（en / zh-TW / zh-CN / ja / ko / es / pt-BR / hi / ar），App 內可切換語言（`AppLocale`，bundle 不拆 locale）。
- 商業模式：免費下載 + 廣告（AdMob banner / rewarded）+ Google Play Billing 一次性購買與訂閱；另有「每週限免」「30 天免費試用」「看廣告續期」等免費機制。花朵（flower）收集系統已用 feature flag 封存（見 [[projects/PaletteWallAndroid/modules/retention-and-trial]]）。
- 營運目標（`team/TEAM_BRIEF.md`）：讓 App 持續營利（收益 > 成本）。北極星指標是首日「成功套用桌布」率、D1/D7 留存、首小時卸載佔比、organic 佔比、ARPDAU；2026-07 的診斷指出最大破口是**新用戶第一小時 activation**（多數新用戶從未打開 DIY 編輯器），因此推 Hero 一鍵套用等功能。詳見 [[projects/PaletteWallAndroid/team]]。

## 技術棧

### Android 端

| 面向 | 技術 |
|---|---|
| 語言 / UI | Kotlin、Jetpack Compose（Material3 + 部分 Material）、Navigation Compose |
| 架構 | MVVM + Clean Architecture（data / domain / ui 三層），詳見 [[projects/PaletteWallAndroid/architecture]] |
| DI | Hilt（`DataModule` / `DomainModule` / `NetworkModule`） |
| 非同步 | Kotlin Coroutines + Flow（ViewModel 對外一律 `StateFlow`） |
| 網路 | Retrofit + OkHttp + Gson；每個請求由 `AuthInterceptor` 加 `x-app-key` / `x-app-version` / `x-app-platform` header，詳見 [[projects/PaletteWallAndroid/api]] |
| 本地儲存 | Room（`WallpaperDatabase`，schema version 10）、SharedPreferences（DIY 桌布快照、TrustedTime、提醒設定等），詳見 [[projects/PaletteWallAndroid/data-model]] |
| 圖片 | Coil（App 層級單一 `ImageLoader`，含 GIF / animated WebP decoder）；assets 內建 `cached_images` 清單 |
| 影音 | Media3 ExoPlayer（依賴存在；待確認實際用途） |
| 背景工作 | WorkManager（`TrialExpiryReminderWorker`） |
| Firebase | Analytics、Crashlytics（含 NDK，為了抓 draw loop 內 libhwui/libskia 的原生 crash）、Remote Config、Cloud Messaging、Storage（圖檔） |
| 變現 | Google AdMob（`play-services-ads`）、Google Play Billing（`billing-ktx`） |
| Play 整合 | In-App Update（flexible / immediate）、In-App Review |
| 測試 | JUnit、Compose UI Test / Espresso（androidTest） |
| CI/CD | Bitrise：自動 build、測試、簽章、AAB；versionCode / versionName 由 Bitrise 注入（git tag） |

- `minSdk 30`、`targetSdk 36`、`compileSdk 36`，JVM target 1.8，KSP 處理 Room 與 Hilt。
- `isMinifyEnabled = false`（release 不混淆）。

### 後端

- Express.js + MongoDB，託管於 Render.com，RESTful API；App 透過 `BuildConfig.BASE_URL` 連線（三個 flavor 目前都指向同一個正式站，dev/staging 的獨立 URL 被註解掉）。
- 圖檔原本放 Firebase Storage，有一份遷移到 Cloudflare R2 + CDN 的計畫（`doc/firebase_to_r2_migration_plan.md`）；dev 上傳工具已走 R2 presigned URL。見 [[projects/PaletteWallAndroid/plans]]。
- 後端 repo 不在本來源內（scripts 的註解提到相對路徑 `web/online-store/backend`）。待確認：後端 repo 是否另行納入 wiki。

## Build variants

`app/build.gradle.kts` 有一個 flavor dimension `env` × 兩種 buildType：

| flavor | app_name | 說明 |
|---|---|---|
| `dev` | PaletteX-d | 預留開發環境（BASE_URL 目前與 prod 相同） |
| `staging` | PaletteX-s | 預留測試環境（同上） |
| `prod` | PaletteX | `isDefault = true` |

| buildType | DEBUG_MODE | Firebase Analytics | Crashlytics |
|---|---|---|---|
| `debug` | true | 停用（manifest placeholder） | 停用 |
| `release` | false | 啟用 | 啟用 |

- **日常開發一律用 `./gradlew assembleProdDebug`**（來源 CLAUDE.md 規定）。`.claude/settings.json` 也只放行 `:app:assembleProdDebug` 與 `:app:lintProdDebug`。
- `DEBUG_MODE` 控制：Remote Config fetch 間隔（debug 0 秒 / release 3600 秒）、是否顯示隱藏的 DIY item、開發者工具頁面等。
- 兩個 BuildConfig 字串欄位從 `local.properties` 或環境變數讀入（**值絕不寫進 wiki**）：
  - `APP_API_KEY`：後端 `x-app-key` 驗證用；CI 必須提供 `APP_API_KEY` secret，否則 release 會帶空 key，後端切到 hard mode 後會被拒。
  - `DEV_UPLOAD_API_KEY`：僅開發者上傳 template 用（`x-api-key`），CI 沒有也無妨（dev 上傳只是 401）。
- release 簽章：本機有 keystore 設定才簽，否則交給 Bitrise 的 Android Sign step。

## 入口點

### `PaletteWallApplication`（`@HiltAndroidApp`）

`app/src/main/java/com/palettex/palettewall/PaletteWallApplication.kt`。除了當 Hilt 根之外，`onCreate()` 依序做：

1. `DebugAnalyticsToggle.applyPersistedState()`：套用 debug 時手動關閉 analytics 的設定。
2. 以 `runBlocking` 從 Room `UserSettings` 讀出語言 tag 寫進 `AppLocale.tag`（之後 `MainActivity.attachBaseContext` 用它包 Context）。
3. 初始化四個 DIY registry（`DiyFrameRegistry` / `DiyBackgroundRegistry` / `DiyDecorationRegistry` / `DiySampleRegistry`，內建 drawable 的名稱對照表）。
4. `Notifications.createChannels()`：建立 `channel_all_users`（FCM 廣播）與 `channel_reminders`（本地提醒）兩個通知頻道。
5. 載入 assets 內的 `ImageCacheList`（內建快取圖清單）。

它也實作 `ImageLoaderFactory`，提供**全 App 唯一**的 Coil `ImageLoader`（記憶體快取 25%、磁碟快取 2%），取代以前各元件各自建 loader 造成的記憶體碎片。

### `MainActivity`（`@AndroidEntryPoint`，唯一 Activity）

`app/src/main/java/com/palettex/palettewall/MainActivity.kt`。單 Activity + Compose，`setContent` 裡放 `PaletteWallTheme` → `NavigationPage`。持有四個 Activity 範圍的 ViewModel：`HomeViewModel`、`TopBarViewModel`、`SettingsViewModel`、`BillingViewModel`。

`onCreate()` 的職責：
- Play In-App Update：先試 flexible、不行再 immediate；下載完成自動 `completeUpdate()` 重啟。
- `initializeServices()`：監聽 `BillingViewModel.isPremium`，非付費才初始化 `MobileAds`；接著拿 FCM token、訂閱 `topic_all_users`、讀版本號、初始化 Firebase Remote Config（成功後 `PaletteRemoteConfig.updateLocalValues()` 並把 `isRemoteConfigInitialized` 設 true）。
- 註冊 `DownloadManager.ACTION_DOWNLOAD_COMPLETE` receiver（靜態桌布下載完成 → 更新下載按鈕狀態）。
- `TrialExpiryReminderScheduler.reschedule()`：從 DB 重新排程試用到期提醒（補 WorkManager 被 force-stop 清掉的情況）。
- 通知點擊路由：讀 intent extra `open_tab` / `notification_source`，只在全新啟動時消費並記 `notification_open` 事件，再交給 `NavigationPage(initialTab)` 跳到對應底部分頁。
- 疊在 NavHost 上的兩個全域 dialog：`NetworkErrorDialog`（onResume 沒網路時）與 `ForceUpdateDialog`（後端 `minVersionCode` 大於已安裝版本時）。

`onResume()`：同步通知開關 user property、檢查網路、`refreshAppSettingsOnResume()`（保持 force-update 與 TrustedTime 新鮮）、載入 banner 廣告、檢查未完成的更新流程。

### AndroidManifest 宣告

| 類型 | 名稱 | 說明 |
|---|---|---|
| Activity | `.MainActivity` | LAUNCHER，鎖直向，SplashTheme |
| Service | `.service.MessagingService` | `FirebaseMessagingService`；收到 FCM 後發通知到 `channel_all_users`，token 更新時重新訂閱 topic |
| Service | `.service.DiyLiveWallpaperService` | `android.service.wallpaper.WallpaperService`，`BIND_WALLPAPER` 權限，metadata `@xml/wallpaper_diy`；DIY 動態桌布的渲染引擎，見 [[projects/PaletteWallAndroid/modules/diy-live-wallpaper]] |
| Worker（非 manifest） | `.service.TrialExpiryReminderWorker` | WorkManager `CoroutineWorker`，試用到期前約 3 天發提醒，見 [[projects/PaletteWallAndroid/modules/notifications-and-workers]] |
| meta-data | AdMob APPLICATION_ID、FCM 預設頻道/圖示/顏色、Analytics / Crashlytics 開關 placeholder | — |

權限：`INTERNET`、`ACCESS_NETWORK_STATE`、`WAKE_LOCK`、`com.google.android.c2dm.permission.RECEIVE`（FCM）、`com.android.vending.BILLING`、`POST_NOTIFICATIONS`。沒有儲存權限——使用者照片一律複製進 app 內部儲存（見 architecture 的工程鐵律第 6 條）。

## Repo 結構

```
PaletteWallAndroid/
  CLAUDE.md            工程規則 + doc 索引（Critical Rules 八條，見 architecture）
  README.md            產品簡介、技術棧
  app/
    build.gradle.kts   flavor / buildType / BuildConfig 欄位 / 依賴
    src/main/java/com/palettex/palettewall/
      data/            Room（local）、Retrofit（remote）、RepositoryImpl、PaletteRemoteConfig
      domain/          model、repository 介面、usecase、DiyAssetModule
      ui/              Compose screens、components、navigation、theme
      service/         DiyLiveWallpaperService、DiyWallpaperConfig、MessagingService、TrialExpiryReminderWorker
      di/              Hilt modules
      util/            FeatureFlags、TrustedTime、Notifications、AppLocale、排程/偏好設定小工具
    src/{dev,staging,prod}/res   各 flavor 的資源覆寫
  doc/                 規劃與設計文件；doc/diy/ 是 DIY 子系統參考（editor、animation、service、remote template、dev tools）
  team/                AI 團隊每週迴圈：TEAM_BRIEF.md（單一事實來源）、reports/（週報）、growth/（ASO、社群、廣告）
  scripts/             set_onetime_price.py（Play 一次性商品定價）、scripts/diy/（從圖片產生 DIY template 並上傳的 Python 工具鏈）
  .claude/             repo 自帶的 agents（data-analyst、growth-marketer、qa-engineer、diy-template-reviewer）與 skills（weekly-report、aso-audit、diy-review…）
```

- `doc/` 的內容摘要在 [[projects/PaletteWallAndroid/plans]]；`team/` 在 [[projects/PaletteWallAndroid/team]]。
- 來源 CLAUDE.md 規定：新的日期筆記寫 `doc/changelog.md`，不寫進 CLAUDE.md。

## 功能模組頁

| 模組 | 內容 |
|---|---|
| [[projects/PaletteWallAndroid/modules/diy-live-wallpaper]] | DIY 編輯器、template / asset 系統、`WallpaperService` 渲染、座標與動畫規則 |
| [[projects/PaletteWallAndroid/modules/monetization]] | AdMob banner / rewarded、Billing 一次購 / 訂閱、Remote Config 廣告開關 |
| [[projects/PaletteWallAndroid/modules/retention-and-trial]] | 免費系統：每週限免、免費試用、續期、TrustedTime；封存的花朵 / 農場系統 |
| [[projects/PaletteWallAndroid/modules/home-and-browsing]] | 首頁 Live / Static 分頁、catalog、搜尋、收藏、全螢幕預覽、Hero 一鍵套用 |
| [[projects/PaletteWallAndroid/modules/notifications-and-workers]] | FCM topic 廣播、本地試用到期提醒、通知點擊路由 |

相關頁：[[projects/PaletteWallAndroid/architecture]]、[[projects/PaletteWallAndroid/api]]、[[projects/PaletteWallAndroid/data-model]]、[[projects/PaletteWallAndroid/plans]]、[[projects/PaletteWallAndroid/team]]。
