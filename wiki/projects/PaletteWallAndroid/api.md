---
title: PaletteWallAndroid — 後端 API 與驗證
source: raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/data/remote, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/di/NetworkModule.kt, raw/PaletteWallAndroid/doc/api_token_auth.md, raw/PaletteWallAndroid/doc/firebase_to_r2_migration_plan.md
updated: 2026-11-24
confidence: high
---

# 後端 API 與驗證

PaletteWall Android 只有一個 Retrofit 介面 `WallpaperApiService`（`app/src/main/java/com/palettex/palettewall/data/remote/api/WallpaperApiService.kt`），對應一個 Express 後端（repo 外的 `online-store/backend`，部署在 Render）。資料庫是 MongoDB，圖檔已從 Firebase Storage 搬到 Cloudflare R2 + CDN。本頁整理端點、驗證、網路層設定與慣例；資料結構細節見 [[projects/PaletteWallAndroid/data-model]]，分層與 DI 見 [[projects/PaletteWallAndroid/architecture]]。

## 1. 端點總表（共 22 個）

Base URL 由 build flavor（`dev` / `staging` / `prod`）在 `app/build.gradle.kts` 以 `BuildConfig.BASE_URL` 注入，三個 flavor 指向不同後端；值不寫進 wiki。路徑皆相對 base URL（推測：base URL 以 `/api/` 結尾，因 `doc/api_token_auth.md` 的後端路由全以 `/api/...` 開頭）。

### 1a. 一般 App 流量（走 Hilt 注入的 client，帶 `x-app-key`）

| Method | 路徑 | 用途 | 主要參數 | 回傳 | 呼叫者 |
|---|---|---|---|---|---|
| GET | `items/photoType/static` | 全部靜態桌布 | — | `List<WallpaperItem>` | `WallpaperRepositoryImpl.getWallpapers()` ← `GetAllWallpapersUseCase` / `WallpaperUseCase.getAll()` ← `HomeViewModel` |
| GET | `items/wallpapers/popular` | 熱門桌布 | `number`(page) | `List<WallpaperItem>` | `getPopularWallpapers()` ← `GetPopularWallpapersUseCase` / `WallpaperUseCase.getPopular()` |
| GET | `items/wallpapers/page` | 分頁 + 分類篩選 | `page`、`pageSize`、`catalog` | `PaginatedResponse` | `getWallpapersByPage()` ← `GetWallpapersByPageUseCase` ← `HomeViewModel`；`SeeMoreViewModel` 直接注入 `WallpaperApiService` 呼叫 |
| GET | `items/search/{searchTerm}` | 關鍵字搜尋 | path `searchTerm` | `List<WallpaperDto>`（唯一經 mapper 轉 domain 的端點） | `searchWallpapers()` ← `WallpaperUseCase.search()` |
| GET | `items/tag/{param}` | 依 tag 取桌布 | path `param` | `List<WallpaperItem>` | 待確認：grep 不到呼叫者，疑為遺留 |
| GET | `items/tag/Anime` | tag 固定為 Anime | — | `List<WallpaperItem>` | 待確認：未被呼叫（遺留） |
| GET | `items/tag/City` | 同上 | — | 同上 | 同上 |
| GET | `items/tag/Painting` | 同上 | — | 同上 | 同上 |
| GET | `items/catalogs/top` | 首頁分類卡 | — | `List<CatalogItem>` | `getCatalogs()` ← `GetCatalogsUseCase` ← `HomeViewModel` |
| GET | `items/boards/top` | 首頁 board（action/value 跳轉卡） | — | `List<BoardItem>` | `getBoards()` ← `GetBoardsUseCase` ← `HomeViewModel` |
| GET | `items/settings/init` | App 啟動設定（版本、廣告等級、DIY 分類、server time、Hero item） | — | `AppSettings` | `getAppSettings()` ← `GetAppSettingsUseCase` ← `HomeViewModel.getAppSettings()`（有 resume 節流） |
| POST | `items/log` | 事件上報（下載、廣告等） | body `LogEventRequest` | 無 body | `sendLogEvent()` ← `SendLogEventUseCase` ← `HomeViewModel.sendLogEvent()` |
| POST | `feedback` | 使用者意見 / bug 回報 | body `FeedbackRequest` | `FeedbackResponse{id}` | `FeedbackViewModel`（直接注入 api） |
| POST | `feedback/upload-url` | 取回饋截圖的 presigned R2 PUT URL | body `FeedbackUploadUrlRequest{contentType}` | `FeedbackUploadUrlResponse{uploadUrl, publicUrl, expiresInSeconds}` | `FeedbackViewModel`（拿到 URL 後用獨立 OkHttpClient PUT） |
| GET | `live_items` | DIY Live Wallpaper 商品清單（含 template JSON） | — | `List<DiyWallpaperItemDto>` | `getDiyLiveItems()` ← `GetDiyLiveWallpapersUseCase` ← `HomeViewModel.loadDiyLiveWallpapers()` |
| GET | `assets` | DIY 素材清單（frames / samples / decorations / backgrounds / stickers / colors） | — | `DiyAssetsResponseDto` | `getDiyAssets()` ← `GetDiyAssetsUseCase` ← `HomeViewModel` → `DiyAssetModule.initialize()` |

備註：`getWallpapers` / `getPopular` / `getWallpapersByPage` / `getCatalogs` / `getBoards` / `getAppSettings` 的回傳型別是 Gson 直接反序列化成 domain 或 DTO 物件，Repository 不做轉換；只有 `items/search` 走 `WallpaperDto → WallpaperItem` 的 mapper（見 data-model 頁）。

### 1b. Dev / admin 專用端點（走 `RetrofitInstance`，另帶 `x-api-key`）

這些端點只在 debug build 的 dev 畫面呼叫，後端以 `requireAdminKey` 保護（Tier A，無 key 直接 401）。

| Method | 路徑 | 用途 | 主要參數 | 回傳 | 呼叫者 |
|---|---|---|---|---|---|
| POST | `live_items` | 上架 DIY template 到正式清單 | body `UploadDiyTemplateRequest` | `UploadDiyTemplateResponse{itemId, message}` | `UploadTemplateBuilderScreen` |
| DELETE | `live_items/{itemId}` | 刪除正式 DIY item | path `itemId` | 無 | `EditDiyLiveWallpaperScreen`（debug 刪除按鈕） |
| GET | `diy_review` | 取 staging（審稿）清單 | — | `List<DiyReviewItemDto>` | `ReviewTemplatePageScreen`、`DevTemplateBuilderScreen` |
| POST | `diy_review` | 存 template 到 staging | body `UploadDiyTemplateRequest` | `UploadDiyTemplateResponse` | `DevTemplateBuilderScreen` |
| DELETE | `diy_review/{itemId}` | 刪 staging item | path `itemId` | 無 | `ReviewTemplatePageScreen` |
| POST | `dev/upload-url` | 取縮圖的 presigned R2 PUT URL | header `x-api-key`、body `DevUploadUrlRequest{path, contentType}` | `DevUploadUrlResponse{uploadUrl, publicUrl, expiresInSeconds}` | `UploadTemplateBuilderScreen.uploadThumbnailToR2()` |

Dev 上傳流程：App 先 POST `dev/upload-url` 取得 presigned URL，再用獨立的 `OkHttpClient` 以**同一個 Content-Type** PUT 檔案到 R2（簽名綁 Content-Type），最後把回傳的 `publicUrl`（CDN URL）寫進 `UploadDiyTemplateRequest.thumbnailUrl`。R2 憑證不進 APK。

`UploadDiyTemplateRequest` 的欄位：`itemId`、`name`、`photoType`（預設 `"diy_live"`）、`price`、`freeDownload`、`freeOnDaysOfWeek`、`flowerCost`、`freeTrialDays`、`maxTrialDays`、`isVisible`、`tags`、`thumbnailUrl`、`thumbnailBlob`、`template: DiyTemplateJson`。`DiyReviewItemDto` 鏡射同一組欄位（`isVisible` 預設 `false`）。`DevTemplateBuilderScreen` 從 `diy_review` 載入後存回時會原樣轉發這些商品元資料，所以後端設定的 `flowerCost` 等值不會被 dev 工具洗掉。

## 2. 驗證機制

細節來源：`doc/api_token_auth.md`（2026-07-15）。設計是 **static API key 雙軌制**，刻意不用 Firebase App Check / Play Integrity（個人專案過度工程；middleware 集中在後端單一檔案，日後要升級只改那裡）。

### 2a. 兩把 key、三個 header

| Header | 誰送 | 內容 | 外洩容忍度 |
|---|---|---|---|
| `x-app-key` | 所有 App 請求（`AuthInterceptor`） | app key，來自 `BuildConfig.APP_API_KEY` | 可接受：APK 可反編譯，定位是提高門檻 |
| `x-app-version` | 所有 App 請求（`AuthInterceptor`） | `versionCode` | — |
| `x-app-platform` | 所有 App 請求（`AuthInterceptor`） | `"android"`（iOS 送 `"ios"`） | — |
| `x-api-key` | admin 網頁、App dev 畫面（`RetrofitInstance.devKeyInterceptor`）、內部工具 | admin key，來自 `BuildConfig.DEV_UPLOAD_API_KEY`；後端過渡期同時接受舊的 dev upload key 與新的 admin key | **絕不可**：永不進 release APK / web bundle |

Key 來源：`app/build.gradle.kts` 以 `buildConfigField` 注入 `APP_API_KEY` 與 `DEV_UPLOAD_API_KEY`，`local.properties` 優先、fallback 環境變數；CI（Bitrise）必須設 `APP_API_KEY` secret，否則 release 帶空 key 出貨。程式碼裡**沒有** hardcode 的 key 值。

### 2b. 後端端點分級

- **Tier A `requireAdminKey`**：所有寫入 / admin 端點（`live_items` POST/PATCH/DELETE、`diy_review` 全部含 GET、`assets` 寫入、`items` 寫入、`dev/upload-url` 等）。立即硬性 401；舊版 App 從不呼叫這些，零影響。
- **Tier B `appKeyAuth`**：App 讀取端點（`items/*` GET 與 `POST items/log`、`live_items` GET、`assets` GET）。依後端 env `APP_AUTH_MODE` 決定：
  - `off`：跳過
  - `soft`（預設）：放行但記 `[app-auth] miss` log（含 path / hasKey / appVersion / ua），用來統計無 key 流量
  - `hard`：無 valid app key 且 Origin 不在白名單 → 401 `APP_KEY_REQUIRED`（web 前端靠 Origin 放行）
- **Tier C 不驗證**：web 商店流程（users / orders / PayPal transaction），只有 CORS。

### 2c. Rollout 與舊版相容

Phase 1 後端上 Tier A hard + Tier B soft → Phase 2 新版 App（帶 `AuthInterceptor`）上架 → Phase 3 觀察 2–6 個月、無 key 流量 < 5% 時切 `hard`（舊 App 讀取 401、內容載不出但不 crash，ViewModel 有 `runCatching`）→ Phase 4 選配加 Play Integrity。壓低舊版占比的工具：`AppSettings.latestVersionCode`（更新橫幅）與 `minVersionCode`（強制更新 dialog）。待確認：目前線上 `APP_AUTH_MODE` 是否已切 hard，程式碼看不出來。

### 2d. Key 輪替

- `APP_API_KEYS` 在後端是逗號分隔清單，支援多把並存：加新 key → 發新版 App → 觀察舊 key 流量歸零 → 從 env 移除舊 key。
- Admin key 外洩：立即換後端 env、更新 admin 網頁 localStorage 與 `local.properties`；過渡期結束後移除後端接受 legacy dev key 的分支。

## 3. 網路層設定

兩套 Retrofit 實例，共用同一個 `WallpaperApiService` 介面：

| | `di/NetworkModule.kt`（Hilt，正常流量） | `data/remote/RetrofitInstance.kt`（dev 畫面專用 object） |
|---|---|---|
| Interceptor 順序 | `AuthInterceptor` | `AuthInterceptor` → `devKeyInterceptor`（加 `x-api-key`） |
| Timeout | connect / read / write 各 30 秒 | 未設定（OkHttp 預設 10 秒） |
| Converter | `GsonConverterFactory` | `GsonConverterFactory` |
| Scope | `@Singleton`，同時提供 `FirebaseAnalytics` | `by lazy` 單例 |
| 使用者 | `WallpaperRepositoryImpl`（經 `DataModule`）、`FeedbackViewModel`、`SeeMoreViewModel` | `UploadTemplateBuilderScreen`、`DevTemplateBuilderScreen`、`ReviewTemplatePageScreen`、`EditDiyLiveWallpaperScreen`（debug 刪除） |

DI 鏈：`NetworkModule` 提供 `OkHttpClient → Retrofit → WallpaperApiService`；`DataModule` 把 `WallpaperApiService` + `ImageCacheDataSource` 組成 `WallpaperRepositoryImpl`（綁 `WallpaperRepository` 介面）；`DomainModule`（`ViewModelComponent`）把 repository 包成各 UseCase。Presigned PUT 到 R2 的上傳（feedback 截圖、dev 縮圖）用另外 new 的純 `OkHttpClient`，不帶任何 header。

## 4. 分頁與錯誤處理慣例

- **分頁**：只有 `items/wallpapers/page` 真正分頁，回 `PaginatedResponse{items, currentPage, totalPages, totalItems, hasMore}`；`HomeViewModel` 與 `SeeMoreViewModel` 以 `hasMore` 決定是否再載。`items/wallpapers/popular` 的 `number` 參數也當 page 用但回傳是純 list。
- **錯誤處理**：`WallpaperRepositoryImpl` 每個方法都是 `withContext(Dispatchers.IO) { try { Result.success(...) } catch (e: Exception) { Result.failure(e) } }`，不分 HTTP 狀態碼；ViewModel 以 `.onSuccess / .onFailure` 處理，失敗只 log，不彈錯誤給使用者。Dev 畫面直接 `runCatching { RetrofitInstance.api.xxx() }`。
- **Gson 與 Kotlin default 的陷阱**（多處註解反覆強調）：Gson 繞過建構子，JSON 缺欄位時 Int → 0、Float → 0f、List → null，**Kotlin default 不生效**。因此 DTO 的新欄位要嘛宣告 nullable（`freeOnDaysOfWeek: List<Int>?`、`thumbnailBlurUrl: String?`、`latestVersionName: String?`），要嘛在 mapping 時 coerce（`maxTrialDays <= 0 → 30`、`startScale == 0f → 1f`、`durationMs <= 0 → 1000`、`photoCards.orEmpty()`）。
- **AppSettings 的 kill switch 慣例**：`minVersionCode = 0` 代表停用強制更新、`serverTimeUtcMs = 0` 代表後端欄位未上線（`TrustedTime` 不同步）、`heroItemId` null/空字串代表隱藏 Hero 區。

## 5. Firebase 服務角色與 R2 遷移

App 依賴 `firebase-bom` 下的 Analytics、Messaging、Remote Config、Crashlytics（含 NDK）；**Firebase Storage 已移除**（2026-07-13）。

| 服務 | 角色 | 關鍵檔案 |
|---|---|---|
| Analytics | 事件追蹤；`NetworkModule` 提供 `FirebaseAnalytics` 單例；`DebugAnalyticsToggle`（Settings 點版本號 10 次）可關掉收集避免污染資料；flavor 以 manifest placeholder 控制是否停用 | `util/DebugAnalyticsToggle.kt`、`util/AdRevenueLogger.kt` |
| Remote Config | 控制廣告：`mode_DownloadReward` / `AdUnitID_DownloadReward` / `mode_BottomBanner` / `AdUnitID_BottomBanner`，mode 0 = 關、1 = debug、其他 = 開；以 `StateFlow` 暴露 | `data/PaletteRemoteConfig.kt` |
| Messaging (FCM) | topic 推播：啟動時訂閱 `topic_all_users`，token 更新時重訂；收到訊息後在 `channel_all_users` channel 發通知。本地提醒（試用到期）走另一個 `channel_reminders` channel，不經 FCM | `service/MessagingService.kt`、`util/Notifications.kt` |
| Crashlytics | 崩潰回報（含 NDK） | `app/build.gradle.kts` |

**圖檔儲存遷移方向**（`doc/firebase_to_r2_migration_plan.md`，2026-07-10 起、Phase 0–4 於 2026-07-13 完成）：所有圖片 URL 存在 MongoDB、App 只用 Coil / `URL.readBytes()` 純 HTTPS 下載，所以 App 讀取端從不依賴 Firebase SDK；遷移把 bucket 全量搬到 Cloudflare R2 並綁自訂 CDN 網域（egress 免費、全球 edge cache），後端 DB 的 2,227 筆 URL 改寫成 CDN URL，App 端改了 `ImageCacheList` 雙格式解析、Carousel 寫死 URL 換 CDN、dev 上傳改走 presigned URL 並移除 `firebase-storage-ktx`。剩餘：Render 環境變數部署與 Phase 5 觀察 90 天後清 Firebase。注意 Cloudflare 會擋 `Python-urllib` UA，App（OkHttp/Coil）不受影響。細節留給 [[projects/PaletteWallAndroid/plans]]。

## 6. 相關頁

- [[projects/PaletteWallAndroid/data-model]] — DTO 欄位、Room、SharedPrefs、DiyTemplate 序列化
- [[projects/PaletteWallAndroid/architecture]] — 分層、DI、資料流
- [[projects/PaletteWallAndroid/modules/diy-live-wallpaper]] — template 怎麼從 API 走到 WallpaperService
- [[projects/PaletteWallAndroid/plans]] — R2 遷移、API auth 等規劃文件摘要
