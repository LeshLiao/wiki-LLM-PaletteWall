---
title: PaletteWallAndroid 架構
source:
  - raw/PaletteWallAndroid/CLAUDE.md
  - raw/PaletteWallAndroid/doc/instructions.md
  - raw/PaletteWallAndroid/doc/diy/wallpaper_service.md
  - raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/di
  - raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/domain
  - raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/data/repository/WallpaperRepositoryImpl.kt
  - raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/data/PaletteRemoteConfig.kt
  - raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/navigation
  - raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/screens/home/HomeViewModel.kt
  - raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/util/FeatureFlags.kt
updated: 2026-11-24
confidence: high
---

# PaletteWallAndroid 架構

產品定位與入口點見 [[projects/PaletteWallAndroid/overview]]。本頁講分層、資料流、DI、導航、ViewModel、設定來源，以及後續開發最常查的**工程鐵律**。

## 1. 分層（Clean Architecture）

`doc/instructions.md` 規定三層；實際 package 多了 `service/`、`di/`、`util/`：

| Package | 職責 | 規範 |
|---|---|---|
| `domain/` | 業務邏輯：`model/`（`WallpaperItem`、`DiyAsset`…）、`repository/`（`WallpaperRepository` 介面）、`usecase/`（每個 use case 一個 class，`operator fun invoke`）、`module/DiyAssetModule`（DIY asset 目錄的記憶體快取 + 查詢） | 理論上不碰 Android framework |
| `data/` | 資料來源：`remote/`（`WallpaperApiService` Retrofit 介面、`AuthInterceptor`、`RetrofitInstance`、`dto/`、`mappers/`）、`local/`（Room `WallpaperDatabase` + entity + dao、`ImageCacheDataSource`）、`repository/WallpaperRepositoryImpl`、`PaletteRemoteConfig` | 實作 domain 的 repository 介面；DTO 用 `toDomain()` 轉 domain model |
| `ui/` | Compose：`screens/<feature>/` 各放 Screen + ViewModel、`components/`（共用元件、modal、skeleton）、`navigation/`、`theme/`、`preview/` | ViewModel 用 `@HiltViewModel`，對外只暴露 `StateFlow`；理論上不知道 Retrofit / Room |
| `service/` | 跨 process / 背景執行：`DiyLiveWallpaperService`（WallpaperService）、`DiyWallpaperConfig`（Service 與 App 之間的 SharedPrefs 契約）、`MessagingService`（FCM）、`TrialExpiryReminderWorker` | Service 不得打網路（鐵律 5） |
| `di/` | Hilt modules（見 §3） | — |
| `util/` | 無狀態工具與小型 prefs：`FeatureFlags`、`TrustedTime`、`Notifications`、`AppLocale`、`NetworkUtil`、`TrialExpiryReminderScheduler`、`TrialReminderPrefs`、`FeedbackPrefs`、`AdRevenueLogger`、`DebugAnalyticsToggle` | — |

**分層並不純粹**（這是事實，不是建議）：
- `WallpaperRepository` 介面直接回傳 data 層 DTO（`PaginatedResponse`、`CatalogItem`、`BoardItem`、`AppSettings`、`DiyWallpaperItemDto`），只有 `WallpaperItem` 與 `DiyAssetsResponse` 是 domain model。
- `domain/usecase/PreloadDiyAssetsUseCase` 依賴 `ui.screens.diy.DiyTemplate` 並直接用 `java.net.URL` 下載；`DiyAssetModule` 用了 Compose `Color`。
- `SeeMoreViewModel` 與 `FeedbackViewModel` 跳過 use case / repository，直接注入 `WallpaperApiService`（Feedback 還注入 `OkHttpClient` 上傳截圖）。
- DIY 的核心型別（`DiyTemplate`、`PhotoCardConfig`、`DecorationConfig`、`StickerConfig`、`TextConfig`、registry、`DiySaveSerializer`）都放在 `ui/screens/diy/`，而 `service/` 與 `domain/` 反向依賴它們。
- 大量 Room 存取（`SettingsViewModel`、`FarmViewModel`、Worker、Scheduler、`PaletteWallApplication`）走 `WallpaperDatabase.getDatabase(context)` singleton，不經 Hilt。

改碼時沿用既有模式即可，不必為了「純」重構；但新功能若牽涉 API，建議照 §2 的鏈路加 use case。

## 2. 資料流

標準鏈路：**Composable → ViewModel（StateFlow） → UseCase → `WallpaperRepository` → `WallpaperApiService`（Retrofit）/ Room DAO**。`WallpaperRepositoryImpl` 每個方法都是 `withContext(Dispatchers.IO) { try { Result.success(api…) } catch { Result.failure(e) } }`，所以 ViewModel 端用 `.onSuccess { }` / `.onFailure { }` 處理，不會拋例外。

### 例 1：首頁 Live 分頁（DIY 動態桌布列表）

1. `PaletteWallPage` 內層 NavHost 進入 `"LiveWallpaper"` → `LiveWallpaperPage` 呼叫 `HomeViewModel.loadLiveHomeData()`（每個 app session 只跑一次；pull-to-refresh 走 `refreshLiveHomeData()`，回前景走 `refreshLiveHomeDataOnResume()`，60 秒節流）。
2. `refreshLiveHomeData()` 併發打四件事：
   - `getAppSettings()` → `GetAppSettingsUseCase` → `GET items/settings/init` → 更新 `appSettings`，順便 `TrustedTime.sync(serverTimeUtcMs)`，並驅動 `forceUpdateRequired` / `updateBannerVersionName` / Hero item。
   - `getBoards()` → `GetBoardsUseCase` → `GET items/boards/top`（首頁輪播）。
   - `loadDiyLiveWallpapers()` → `GetDiyLiveWallpapersUseCase` → `GET live_items` → DTO 轉 `DiyWallpaperItem`（補 `maxTrialDays` 預設 30、過濾 `isVisible`，DEBUG 可顯示隱藏項）→ `_diyLiveWallpapers`。
   - `loadDiyAssets()` → `GetDiyAssetsUseCase` → `GET assets` → `DiyAssetModule.initialize()`（之後編輯器、preload、Service 冷啟動以外的 asset URL 查詢都靠它）。
3. `LiveWallpaperPage` 以 `collectAsState()` 訂閱 `diyLiveWallpapers` / `isDiyLoading` / `appSettings.live_catalog`，依 catalog 分組渲染 `RowDiyLiveWallpaper` / `GridDiyLiveWallpaper`；點擊 → `outerNav.navigate("edit_diy_live_wallpaper/{itemId}")`。

### 例 2：首頁 Static 分頁（靜態桌布分頁載入）

`loadStaticHomeData()` → `setCurrentCatalog("Wallpapers")` → `refreshStaticHomeData()`：`resetPagination()` + `loadMoreWallpapers()`（`GetWallpapersByPageUseCase(page, 36, catalog)` → `GET items/wallpapers/page`）+ `initAllCatalogs()`（anime / space / minimalistic / nature / landscape 各抓 12 張填 `catalogWallpapers` map）。捲到底再呼叫 `loadMoreWallpapers()` 取下一頁，`isLastPage` 停止。

### 例 3：DIY 儲存並套用（App → Service 的單向資料流）

編輯器 `doSaveAndApply()` → 同時寫 Room `DiySaveTemplate`（草稿，可重開編輯）與 `DiyWallpaperConfig.save()`（SharedPrefs `diy_wallpaper`，含 `template_json` 快照、使用者圖片 `file://` URI、transform、背景、貼紙、文字）→ 以 `commit()` 同步落盤 → 送 `ACTION_CHANGE_LIVE_WALLPAPER` intent → 系統啟動 `DiyLiveWallpaperService` → Engine 用 `DiyWallpaperConfig.loadTemplate()` 讀回，**不打網路**。詳見 [[projects/PaletteWallAndroid/modules/diy-live-wallpaper]]。

### 本地資料

Room `WallpaperDatabase`（version 10，有 2→3 … 9→10 的手寫 migration）包含：`LikedWallpaper`、`LikedDiyWallpaper`、`UserSettings`、`DiySaveTemplate`、`DevSavedTemplate`、`DiyUnlockRecord`、`FlowerBasket`。表結構與 SharedPrefs 清單見 [[projects/PaletteWallAndroid/data-model]]。

## 3. Hilt DI

| Module | 安裝範圍 | 提供 |
|---|---|---|
| `NetworkModule` | `SingletonComponent` | `OkHttpClient`（`AuthInterceptor`、30 秒 connect/read/write timeout）、`Retrofit`（`BuildConfig.BASE_URL` + Gson）、`WallpaperApiService`、`FirebaseAnalytics` |
| `DataModule` | `SingletonComponent` | `ImageCacheDataSource`、`WallpaperRepository`（綁到 `WallpaperRepositoryImpl(apiService, imageCacheDataSource)`） |
| `DomainModule` | `ViewModelComponent`（`@ViewModelScoped`） | 十個 use case：`WallpaperUseCase`、`GetPopularWallpapersUseCase`、`GetAllWallpapersUseCase`、`GetWallpapersByPageUseCase`、`GetCatalogsUseCase`、`GetBoardsUseCase`、`GetAppSettingsUseCase`、`SendLogEventUseCase`、`GetDiyLiveWallpapersUseCase`、`GetDiyAssetsUseCase` |

補充：
- `GetDiyLiveWallpapersUseCase` / `GetDiyAssetsUseCase` 同時有 `@Inject constructor` 與 `@Provides`；`PreloadDiyAssetsUseCase` 沒有依賴，直接 `PreloadDiyAssetsUseCase()` 建構。
- 開發者工具（template builder、review、debug delete）不走 Hilt，改用 `data/remote/RetrofitInstance`——同一個 `AuthInterceptor` 再加上一個把 `DEV_UPLOAD_API_KEY` 塞進 `x-api-key` 的 interceptor。正式流量一律走 `NetworkModule`。
- Room 沒有 Hilt binding（見 §1 的不純粹清單）。

## 4. 導航

兩層 NavHost：

**外層 `NavigationPage`**（`ui/navigation/NavigationPage.kt`，`sealed class Screen`）：

| `Screen` | route | 對應 Composable | 備註 |
|---|---|---|---|
| `PaletteWallPage` | `PaletteWallPage?tab={tab}` | `PaletteWallPage`（`HomeScreen.kt`） | start destination；`tab` 預設 `LiveWallpaper`，通知點擊可帶 `Favorite` 等 |
| `Search` | `search` | `SearchPage` | 自己 `hiltViewModel<SearchViewModel>()` |
| `Fullscreen` | `fullscreen/{itemId}` | `FullscreenScreen` | 靜態桌布全螢幕預覽 / 下載 |
| `SeeMore` | `see_more/{catalog}` | `SeeMorePage` | 某 catalog 的分頁列表 |
| `EditDiyLiveWallpaper` | `edit_diy_live_wallpaper/{itemId}?fromCollections={bool}` | `EditDiyLiveWallpaperScreen` | DIY 編輯器 |
| `DevTemplateBuilder` | `dev_template_builder?templateId={long}&reviewItemId={string?}` | `DevTemplateBuilderScreen` | 開發者：建 template |
| `UploadTemplateBuilder` | `upload_template_builder` | `UploadTemplateBuilderScreen` | 開發者：上傳 template |
| `ReviewTemplatePage` | `review_template_page` | `ReviewTemplatePageScreen` | 開發者：審核 `diy_review` |
| `Farm` | `farm_page` | `FarmScreen` | 花朵農場（feature flag 關閉中） |
| `Feedback` | `feedback_page?startOnImprove={bool}&startOnRate={bool}` | `FeedbackScreen` | 建議 / 評分流程 |
| `BugReport` | `bug_report_page` | `BugReportScreen` | 含截圖上傳 |

轉場是左右 slide（自訂 CubicBezier easing）。`initialTab != null` 時以 `popUpTo(inclusive)` + `launchSingleTop` 重建 `PaletteWallPage`，因為內層只在首次 composition 時尊重 `startDestination`。

**內層（`PaletteWallPage` 的底部分頁 NavHost）**：`LiveWallpaper`（首頁，Home icon）、`StaticWallpaper`、`Favorite`、`Settings`，另有 `AboutUs` 與內層 `fullscreen/{itemId}`。`TopBarViewModel` 依 route 切換標題。

**慣例**：使用者觸發的返回一律用 `NavController.popBackStackSafe()`（`NavControllerExt.kt`）——只在目前 destination 為 RESUMED 時 pop，避免 pop 動畫期間重複點擊把 start destination 也 pop 掉造成黑畫面。

## 5. ViewModel 清單

| ViewModel | 範圍 / 注入 | 負責的狀態 |
|---|---|---|
| `HomeViewModel`（`open class`，約 980 行） | Activity；注入 `FirebaseAnalytics`、8 個 use case、`@ApplicationContext` | 幾乎所有首頁 / 瀏覽狀態：`appSettings`、`todayDayOfWeek`（TrustedTime）、`catalogs` / `boards`、`wallpapers`（分頁）/ `allWallpapers` / `catalogWallpapers` / `catalogConfigs`、`carouselWallpapers`、`collectionWallpapers`、`fullScreenWallpapers`、`diyLiveWallpapers` / `isDiyLoading`、`selectedTags`、當前圖片 (`currentImage` / `currentBlurImage` / `isCurrentFreeDownload`)、顏色選取、`downloadBtnStatus` / `loadAdsBtnStatus` / `isBottomAdsLoaded`、`isRemoteConfigInitialized`、版本與更新（`versionName`、`updateBannerVersionName`、`forceUpdateRequired`）、`currentCatalog`、`scrollToTopTrigger`、`isFullScreen` |
| `BillingViewModel`（約 590 行） | Activity；注入 context | Google Play Billing：`isPremium`、`purchasedProductIds`、`isAlreadyPurchase`、價格快取 `ProductPrice`；`launchBillingFlow`（訂閱）、`launchBillingFlowWithOneTimePurchase`、`getOneTimePurchasePrice`、`getSubscriptionPrices`、acknowledge 重試 |
| `TopBarViewModel` | Activity；無依賴 | `isTopBarVisible`（隨捲動隱藏）、`topBarTitle` |
| `SettingsViewModel`（`AndroidViewModel`，非 Hilt） | Activity | `isDarkThemeEnabled`、`languageTag`、`themeId`（預設 `midnight_gold`）；讀寫 Room `UserSettings` |
| `SearchViewModel` | 畫面；注入 `WallpaperUseCase` | `searchQuery`（debounce）、`searchResults`、`isLoading`、`errorMessage`、`uiState` |
| `SeeMoreViewModel` | 畫面；注入 `WallpaperApiService` | 單一 catalog 的分頁 `wallpapers`、`isLoading`、`isRefreshing` |
| `FeedbackViewModel` | 畫面；注入 context、`WallpaperApiService`、`OkHttpClient` | `submitState`（Idle / Submitting / Success / Error）；建議與 bug report 送出、截圖先取 upload URL 再 PUT |
| `FarmViewModel`（`AndroidViewModel`，非 Hilt） | 畫面 | `FarmUiState`（花朵、連續簽到、每日獎勵）；僅在 `FeatureFlags.FLOWER_SYSTEM_ENABLED` 時有意義 |

`EditDiyLiveWallpaperScreen` 與 dev 工具沒有專屬 ViewModel，狀態放在 Composable 的 `remember` 裡（`DevTemplateState` 等），並共用 `HomeViewModel` / `BillingViewModel` / `TopBarViewModel`。

## 6. 設定來源：Remote Config、AppSettings、FeatureFlags

三種「開關」各管不同層級，別混用：

| 來源 | 位置 | 管什麼 | 更新方式 |
|---|---|---|---|
| **Firebase Remote Config** → `PaletteRemoteConfig`（`data/PaletteRemoteConfig.kt`，object） | Firebase Console | **廣告**：`mode_DownloadReward` / `AdUnitID_DownloadReward`（rewarded）、`mode_BottomBanner` / `AdUnitID_BottomBanner`（banner）。mode `0` = 關、`1` = debug（測試 ad unit）、其他 = 正式。暴露 `StateFlow` 與 `shouldShowRewardAds()` / `shouldShowBannerAds()` / `getAdUnitId()` 等 helper | `MainActivity.initializeRemoteConfig()` 在 `fetchAndActivate` 成功後呼叫 `updateLocalValues()`；預設值在 `res/xml/remote_config_defaults`；debug 不限制 fetch 間隔，release 1 小時 |
| **後端 `AppSettings`**（`GET items/settings/init`） | 自家後端 | **產品行為**：`adsLevel`、`live_catalog`（DIY 分類順序與多語名稱）、`latestVersionCode` / `latestVersionName`（更新橫幅）、`minVersionCode`（強制更新）、`serverTimeUtcMs`（TrustedTime 錨點）、`heroItemId`（Hero 一鍵套用的 kill switch） | `HomeViewModel.getAppSettings()`，Live 分頁載入與 onResume（60 秒節流）。Gson 會繞過 Kotlin 預設值，缺欄位變 0 / null，所以版本比較與 TrustedTime 都設計成「0 = 未啟用」 |
| **`FeatureFlags`**（`util/FeatureFlags.kt`，編譯期常數） | 程式碼 | 目前只有 `FLOWER_SYSTEM_ENABLED = false`：花朵 retention 系統（農場、簽到、花朵兌換 / 續期、計數、tag）整套封存但程式保留，設 true 即復活 | 改碼重新 build |

另外 `BuildConfig.DEBUG_MODE` 控制開發者功能（隱藏 DIY item、dev 畫面、analytics 切換）。

## 7. 工程鐵律（整理自來源 CLAUDE.md「Critical Rules」）

這八條是後續開發最常踩到的地方，改 DIY 相關程式前先對一遍。

### 鐵律 1：座標與尺寸全用 canvas 比例，且寬高都以「canvas 寬度」為基準

`CardPosition(x, y)` 是 0–1 的 canvas 比例，代表**卡片中心點**。卡片的 `widthFraction` 與 `heightFraction` **都是 canvas 寬度的比例**（不是 dp，也不是各自對寬 / 高）：

```
offsetX = x × canvasW − canvasW × widthFraction / 2
offsetY = y × canvasH − canvasW × heightFraction / 2
wPx = widthFraction  × canvasWidthPx   （Service 端免 density 換算）
hPx = heightFraction × canvasWidthPx
```

唯一的不對稱、也是最常見的 bug：**height 是 canvas 寬度的比例，但 `End_y`（位置 y）是 canvas 高度的比例**。細節在 `doc/diy/animation_system.md`。

### 鐵律 2：Service draw loop 內零 allocation，動畫播完就停

`DiyLiveWallpaperService` 的 draw 路徑內**禁止** `new Paint / Shader / Matrix / Bitmap / Pair` 等任何配置。需要的物件宣告成 Engine 欄位重用，或在 `loadBitmaps()` 預先建好（例如 `shadowPaint`、`blurFilterCache`、vignette shader、`typefaceCache`）；位置 / 旋轉 / 縮放 / alpha 用 `tempPos: FloatArray(2)` 與既有 helper 寫回，不要回傳 `Pair`。
動畫是 play-once：`Phase.ANIMATING → PAUSING`，`doFrame` 只在 `ANIMATING` 時 `postFrameCallback`，進入 `PAUSING` 後 loop 必須停（實機量測：靜止時主執行緒 CPU 從每秒 ~120ms 降到 ~20ms）。`onVisibilityChanged(true)` 重設為 `ANIMATING` 重播一次。

### 鐵律 3：新增欄位一定跑 checklist

- 在 `EditDiyLiveWallpaperScreen` 新增可編輯狀態 → 必須同步：`DiySaveTemplate` column、`DiySaveSerializer`、Room MIGRATION、`doSaveAndApply()` 寫入、`LaunchedEffect` 載入、`committed*` baseline 與 `hasEdits`。完整 6 + 4 步在 `doc/diy/editor.md`。
- `PhotoCardConfig` / `DecorationConfig` / `StickerConfig` / `TextConfig` / `DiyTemplate` 等 config / DTO 增刪改欄位 → 跑 `diy-template-reviewer` agent（`.claude/agents/`）追整條 pipeline，並更新 `doc/diy_live_wallpaper_data_flow.md`（哪個欄位在哪一階段被 drop）。

### 鐵律 4：序列化要向後相容

- Asset / drawable 一律存 **name 字串**（如 `diy_frame_0001`），絕不存 resource ID（每次 build 都會變）。
- Enum 存字串，反序列化用 `runCatching { valueOf() }.getOrDefault(...)` 安全回退。
- `DiyTemplate` 新欄位**必須有 default value**：App 更新後 SharedPrefs 裡的舊 JSON 仍要能讀。
- 顏色存 `"#AARRGGBB"` 字串（`android.graphics.Color.parseColor()`）。

### 鐵律 5：WallpaperService 完全獨立

- Service **絕不**做網路請求（尤其 draw loop 內），也**不用** `DiyTemplateRegistry`。
- Template 唯一來源是 SharedPrefs 快照：Save 時 `DiyTemplate.toUploadJson()` → `SharedPrefs["template_json"]`；Service 用 `DiyWallpaperConfig.loadTemplate()` 讀回。
- `DiyWallpaperConfig.save()` 必須用 `commit()`（同步），不可 `apply()`——否則 Service 可能在落盤前讀取，首次設定會是空白畫面。

### 鐵律 6：使用者挑圖當下就複製進內部儲存

在 picker callback（`onImagePicked` / `onBatchImagesPicked` / `onBackgroundSelected`）當下呼叫 `DiyImageStorage.copyToInternal()` 複製到 `filesDir/diy_user_images/`，state 存穩定的 `file://` URI；Save 只是序列化既有 state。**絕不使用 `takePersistableUriPermission`**（Photo Picker 的 URI 沒有 persistable grant，會丟 `SecurityException`；就算沒丟，grant 也可能在 Service 這個獨立 process 讀取前被撤銷）。

### 鐵律 7：Compose 動畫慣例（`WallpaperCanvas`）

- 每個元素一個 `Animatable`；position 用 `Animatable<Offset, AnimationVector2D>` + `Offset.VectorConverter`。
- `offset { }` lambda 是 `Density` scope：offset 以 dp 儲存，用 `.dp.roundToPx()` 轉換。
- `LaunchedEffect(canvasWidthDp, canvasHeightDp)` 必須 guard `mode == PREVIEW`，否則系統 bar 消失觸發 resize 時會 `snapTo(endPosition)` 取消進行中的動畫。
- Compose 與 Service 的縮放基準要一致：`ContentScale.Fit` ↔ `fitScaleBitmap`；easing 都是 `PathInterpolator(0.4f, 0f, 0.2f, 1f)`。

### 鐵律 8：`DiyTemplate` 與 `DiyWallpaperItem` 職責分離，價格不 hardcode

`DiyTemplate` 只存動畫 / 渲染設定；商品元資料（`itemId`、`name`、`freeDownload`、`tags`、試用天數…）在 `DiyWallpaperItem`。不要加 hardcode 的 `price`，售價一律即時從 Google Play Billing 查（`BillingViewModel.getOneTimePurchasePrice()`）。

## 8. 已知裝置行為（摘要）

完整說明在 `doc/diy/wallpaper_service.md`「注意事項」：

| 現象 | 原因 | 狀態 |
|---|---|---|
| 動態桌布**無法直接單獨設到鎖定螢幕**（選「鎖定螢幕」沒反應，改選「桌面」後兩邊才都出現） | OEM（三星、小米等）的 WallpaperManager 要求引擎先以桌面模式初始化過 | 無法從 App 端繞過；建議使用者第一次先選「桌面」或「桌面 + 鎖定螢幕」 |
| 首次設定後畫面空白，重開機再設才正常 | `DiyWallpaperConfig.save()` 用 `apply()`，Service 在落盤前就讀 | 已修正：改 `commit()`（鐵律 5） |
| Service 的圖片縮放比 Preview 大 | Preview 用 `ContentScale.Fit`，Service 用 `fillWidthScaleBitmap` | 已修正：Service 改 `fitScaleBitmap`（鐵律 7） |
| Decoration 在 Service 被拉伸成正方形 | `createScaledBitmap` 忽略長寬比 | 已修正：改 `fitScaleBitmap` 等比縮放置中 |
| App 更新 / 重開機後 sample 與 background 消失，使用者照片與文字不受影響 | preload 快取檔以後端真實 ext 命名，但 Service 冷啟動時 `DiyAssetModule` 未初始化（Service 不打網路），fallback 猜 ext 猜錯 → 快取 miss | 已修正（2026-07-10）：精確檔名 miss 後加 ext-agnostic 掃描 `diy_assets/{id}.*` |

## 相關頁

[[projects/PaletteWallAndroid/overview]] · [[projects/PaletteWallAndroid/api]] · [[projects/PaletteWallAndroid/data-model]] · [[projects/PaletteWallAndroid/modules/diy-live-wallpaper]] · [[projects/PaletteWallAndroid/modules/monetization]] · [[projects/PaletteWallAndroid/modules/retention-and-trial]] · [[projects/PaletteWallAndroid/modules/home-and-browsing]] · [[projects/PaletteWallAndroid/modules/notifications-and-workers]] · [[projects/PaletteWallAndroid/plans]]
