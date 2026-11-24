---
title: Home 與瀏覽（首頁結構、搜尋、全螢幕、收藏、下載、設定、Onboarding、圖片快取）
source: raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/screens/home/, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/screens/search/, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/screens/filter/, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/screens/seemore/, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/screens/fullscreen/, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/screens/likecollection/, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/screens/settings/, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/screens/welcome/, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/components/, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/navigation/NavigationPage.kt
updated: 2026-11-24
confidence: medium
---

# Home 與瀏覽

App 的殼層：首頁四個 tab（Live / Static / Favorite / Settings）、靜態桌布的瀏覽／搜尋／下載／設定桌布、收藏頁、設定頁與首次啟動引導。DIY 編輯器本身見 [[projects/PaletteWallAndroid/modules/diy-live-wallpaper]]。

相關頁：[[projects/PaletteWallAndroid/architecture]]（導航與 DI）、[[projects/PaletteWallAndroid/api]]（端點）、[[projects/PaletteWallAndroid/modules/monetization]]（下載 gating）、[[projects/PaletteWallAndroid/modules/retention-and-trial]]（Free Today、收藏頁 trial）、[[projects/PaletteWallAndroid/modules/notifications-and-workers]]（更新 banner、網路 dialog）。

## 1. 導航結構

`ui/navigation/NavigationPage.kt` 的外層 `NavHost`（`Screen` sealed class）：

| Route | 畫面 |
|---|---|
| `PaletteWallPage?tab={tab}`（start） | `PaletteWallPage`（HomeScreen）— `tab` 預設 `LiveWallpaper`；`?tab=Favorite` 用於收藏導向與通知點擊 |
| `search` | `SearchPage` |
| `fullscreen/{itemId}` | `FullscreenScreen` |
| `see_more/{catalog}` | `SeeMorePage` |
| `edit_diy_live_wallpaper/{itemId}?fromCollections=` | DIY 編輯器 |
| `dev_template_builder?templateId=&reviewItemId=`、`upload_template_builder`、`review_template_page` | Dev 工具 |
| `farm_page` | 農場（flag 關閉，無入口） |
| `feedback_page?startOnImprove=&startOnRate=`、`bug_report_page` | 回饋 |

`PaletteWallPage` 內層 `NavHost`：`LiveWallpaper`（start）/ `StaticWallpaper` / `Favorite` / `AboutUs` / `Settings`。非預設 tab 是用 `LaunchedEffect` **navigate** 過去（內層 stack 變 `[LiveWallpaper, tab]`），所以系統返回會回首頁 tab 而非退出 App；要落到非預設 tab 時外層必須 `popUpTo(PaletteWallPage) { inclusive = true }` 重建。`NavControllerExt.popBackStackSafe()`（只在 current entry RESUMED 時 pop）避免轉場中連擊造成 double pop 黑屏。

## 2. HomeScreen 結構

```
PaletteWallPage (HomeScreen.kt)
├─ ModalNavigationDrawer（DrawerContent；手勢與漢堡鈕目前暫時關閉）
│  └─ Scaffold
│     ├─ topBar: HomeTopBar（CenterAligned；標題依 tab；搜尋 icon；FlowerCounterBadge 隨 flag 隱藏）
│     ├─ bottomBar: BottomBarBox（4 個 Rounded icon tab + 底部 banner AdView）
│     └─ 內層 NavHost：LiveWallpaperPage / MainPageContent / LikeCollection / SettingsPage / AboutUs
├─ DiyAssetLoadingOverlay（DIY asset 預下載進度，蓋住含底部導覽的全頁）
└─ StartedGuidePage（一次性首啟 overlay，最上層；500ms fade out）
```

- `TopBarViewModel`：`isTopBarVisible`（依捲動 delta 佇列判斷顯示／隱藏）、`topBarTitle`（由 `currentBackStackEntryAsState` 同步）。
- `HomeViewModel`（`@HiltViewModel`，MainActivity 單一實例）主要 state：`appSettings`、`todayDayOfWeek`、`catalogs` / `boards`、`wallpapers`（分頁靜態 grid）、`catalogWallpapers: Map<key, List>`、`carouselAllWallpapers`、`collectionWallpapers`、`fullScreenWallpapers`、`diyLiveWallpapers` + `isDiyLoading`、`downloadBtnStatus`（0 未下載 / 1 下載中 / 2 完成）、`isBottomAdsLoaded`、`updateBannerVersionName`、`forceUpdateRequired`、色彩搜尋的 `firstSelectedColor` / `secondSelectedColor` / `selectedTags`、`isRemoteConfigInitialized`。
- **Per-tab bootstrap**：`loadLiveHomeData()`（boards + DIY + assets + settings）與 `loadStaticHomeData()`（catalogs + 分頁）各自只跑一次；`refresh*OnResume()` 以 `elapsedRealtime()` 戳記節流 60 秒；`refreshAppSettingsOnResume()` 由 `MainActivity.onResume` 呼叫（強制更新檢查與 `TrustedTime.sync` 不依賴進 DIY tab）。
- `HERO_ITEM_ID` 常數與 `DiyPreloadPurpose { EDITOR, QUICK_APPLY }`：見 DIY 頁 Hero 一節。
- 進度歸零時序陷阱：preload 進度必須在設定 request 的地方歸零，不是在 `LaunchedEffect`（否則先閃前一輪的 100%）。

### 2.1 LiveWallpaperPage（Live tab）

LazyColumn 由上而下：頂部 spacer → `AppUpdateBanner`（後端 `latestVersionCode` 高於安裝版時；原位是 `DiyTipsCarousel`，兩者同高避免跳動，目前 tips 與 boards `AutoScrollImagePager` 皆註解隱藏）→ `AppUpdateRewardButton`（flag）→ DIY 區：`GridDiyLiveWallpaperSkeleton` 或 `HeroQuickApplySection`（`heroItemId` 解析得到時）→ 「Free Today」群組（`isFreeNow` 篩選；`Daily` 漸層 tag；右下「下一次更新時間」用 `TrustedTime.nextRotationMs()`）→ 各 tag 分類 `gridDiyLiveWallpaperSection`（**每個 item 獨立 LazyColumn item**，不可整段包成一個 `item {}`，否則所有動畫縮圖同時 compose）→ `feedbackPromptRow` → 底部 spacer。支援 pull-to-refresh（先 `NetworkUtil` 檢查）。

`DiyLiveWallpaperCard`：9:20 直式卡；縮圖 `rememberDiyThumbnailModel()`（drawable → bundled asset → filesDir → CDN），動畫 WebP 單輪播放後延遲 2 秒重播（Coil 回傳 `ScaleDrawable` 包裝，要解包才拿得到 `AnimatedImageDrawable`；**不可 unregisterAnimationCallback**，會與框架 race 造成 NPE）；overlay 期間以 `LocalDiyThumbnailAnimationsPaused` 凍結成靜態首幀。FREE tag 用 `isFreeNow`。

### 2.2 MainPageContent（Static tab）

`Material3Carousel`（5 張固定 collection 封面，CDN URL，點擊 `see_more/{key}`）→ 依 `catalogConfigs` 渲染 `CatalogStaticRow`（`RowStaticWallpaper` + 可選 `RowTag`，See More → `see_more/{key}`）→ 分頁靜態 grid（`wallpapers.chunked(3)`，接近底部時 `loadMoreWallpapers()`；`shouldLoadMore()` 防重入）→ 底部 loading → pull-to-refresh。底部 `BottomBarBox` 預先初始化 `AdManager` 的 AdView。

### 2.3 其他首頁元件

| 元件 | 用途 |
|---|---|
| `CatalogRow` | 分類卡片列（含 skeleton） |
| `AutoScrollImagePager` / `AutoScrollCarousel` | boards 輪播（單張時不輪播、不顯示指示點）；目前在 Live tab 註解隱藏 |
| `GridDiyLiveWallpaper` | `DiyCategory(key, title, items)`、`buildDiyCategories()`、`gridDiyLiveWallpaperSection()`（`trailing` / `footer` slot） |
| `RowStaticWallpaper` / `StaticWallpaperCard` | 橫向靜態桌布列與單卡（progressive 載入、鑽石付費徽章） |
| `DiyTipsCarousel` | 4 條使用提示，每 5 秒自動輪播；`LaunchedEffect` 必須 key 在 `settledPage`；CJK 文字要 `wrapContentHeight(unbounded = true)`（目前隱藏） |
| Skeleton | `ImageSkeletonLoader`、`GridRowSkeleton`、`GridDiyLiveWallpaperSkeleton`、`Material3CarouselSkeleton`、`RowWallpapersSkeleton`、`AutoScrollImagePagerSkeleton`、`TitlesSkeleton`、`SkeletonParagraph` |
| `DrawerContent` | 側欄：About、分類列表、農場入口（flag）；目前漢堡鈕與手勢暫時關閉（還原改回 `gesturesEnabled = !isFullScreen`） |
| `DateTimeDisplay` | DIY PREVIEW 疊的日期時間（靜態快照，不即時跳） |

## 3. 瀏覽與搜尋

| 畫面 | 檔案 | 行為 |
|---|---|---|
| 搜尋 | `ui/screens/search/SearchScreen.kt`、`SearchViewModel.kt` | `searchQuery` debounce 500ms → `WallpaperUseCase.search()`（`GET items/search/{term}`）；三欄 grid，點擊 `fullscreen/{itemId}`；錯誤／空狀態訊息 |
| 色彩篩選 | `ui/screens/filter/FilterScreen.kt`（`FilterPage`、`WallpaperCarousel`）、`ui/components/ColorPaletteMatrix.kt`、`ColorInfoDisplay.kt`、`FilterChipRowPage.kt` | 選最多兩個顏色 + tags；`HomeViewModel.updateFilteredWallpapers()` 用 RGB 距離對桌布色票（`#` 開頭的 tag）做相似度，tags 用 AND 邏輯；無篩選時隨機。`ColorInfoDisplay` 顯示 ARGB 字串。待確認：目前 UI 入口在哪（HomeScreen grep 未見 route），可能是舊功能 |
| See More | `ui/screens/seemore/SeeMoreScreen.kt`、`SeeMoreViewModel.kt` | 單一 catalog 的 36/頁分頁（`GET items/wallpapers/page`），接近底部 3 項時載入，pull-to-refresh |
| 全螢幕 | `ui/screens/fullscreen/FullscreenScreen.kt`（~800 行） | 左右滑切換（`fullScreenWallpapers` 列表）；`setCurrentProductId()` 更新購買狀態；按鈕列：Like、Share、Info、Download/Set；底部 Preview 鈕與 DIY 編輯器同款；`ShowDownloadDialog` 顯示下載訊息 |
| 收藏 | `ui/screens/likecollection/LikeCollectionScreen.kt`（~1000 行） | 分頁 SAVED / FAVORITES / PURCHASED；DIY 與靜態混排；`LikedWallpaper`（靜態，存 `wallpaperId` + `imageUrl`）與 `LikedDiyWallpaper`（`itemId`）兩張表；SAVED 分頁含 trial 倒數、續期、購買、刪草稿、到期提醒 toggle（見 retention 頁）；愛心在卡片右上 |

## 4. 靜態桌布下載與設定桌布

```
FullscreenScreen「Download / Set」
├─ premium → AvailableDownloadPremiumModal → downloadImage()
├─ 免費 → NormalModal：看 Rewarded Ad（PaletteRemoteConfig.shouldShowRewardAds）→ onEarned → downloadImage()
└─ 付費 → NormalModal 付費鈕 → OneTimePurchaseModal / SubscriptionModal
downloadImage() → AndroidDownloader.downloadFile(url)（DownloadManager，存 Downloads/PaletteWall-{md5 前 8 碼}.jpg）
→ MainActivity 的 ACTION_DOWNLOAD_COMPLETE receiver → updateDownloadBtnStatus(2)
→ 自動開系統「設定桌布」：優先 MEDIAPROVIDER_URI content://，手動組 CROP_AND_SET_WALLPAPER intent（避開 MIME 檢查）
   → 失敗 fallback ACTION_ATTACH_DATA chooser
→ 回 App ON_RESUME：NotificationOptIn.maybeRequest() 或 InAppReview.requestIfEligible()
```

- `Downloader` 介面 / `AndroidDownloader` 實作；請求限 WiFi（`NETWORK_WIFI`）。待確認：`AndroidDownloader` 加了一個字面 placeholder 的 `Authorization: Bearer <token>` header（看起來是殘留，非真實憑證）。
- `ShareButton` / Fullscreen 內的分享：`ACTION_SEND` 文字（`firebaseShareEvent`）；retention 計畫想加浮水印出圖，未做。
- `LikeButton`：切換 Room liked 表（`firebaseLikeEvent`）。

## 5. Onboarding

| 畫面 | 說明 |
|---|---|
| `StartedGuideScreen.kt`（`StartedGuidePage`） | 首啟 overlay：Welcome 段（品牌列 + `WelcomeHeroVideo` ExoPlayer mp4，`PlayerView` 必須 `surface_type="texture_view"` 否則 fade out 時影片殘留）→ 3 頁 `HorizontalPager` 功能輪播；CTA Browse / Next / Explore now；右上 X 與 back（逐步回退）可關；`welcome_seen` SharedPrefs 鏡像 + Room 雙寫 |
| `WelcomeScreen.kt` | 舊版 `WelcomeOverlay`（5 秒倒數鎖、`TimedCloseButton`）已 `@Deprecated`；保留色票與 `WelcomeHeroVideo` |
| `DiyCoachmarkOverlay` | 首次進 DIY 編輯器的 Photos 提示（`DiyCoachmarkPrefs`） |

## 6. 設定與其他

| 畫面 | 說明 |
|---|---|
| `SettingsScreen.kt`（`SettingsPage`） | 區塊：FEEDBACK（意見反饋 / 錯誤回報）、GENERAL（Dark Mode、Theme picker 目前隱藏、Language、聯絡開發者 mailto、Play 評分）、LEGAL（政策連結）、INFORMATION（版本；**點版本列 10 次**切換 `DebugAnalyticsToggle`，讓 sideload release 不污染 Firebase）、`PremiumBanner`、`DeveloperSettingsSection`（DEBUG） |
| `SettingsViewModel` | `AndroidViewModel` + `UserSettingsDao`（`isDarkThemeEnabled`、`languageTag`、`themeId`，預設 `midnight_gold`）；`setAppLanguage()` 先同步寫 `AppLocale.tag` 再存 DB，`MainActivity.recreate()` |
| `LanguagePickerDialog` | 系統預設 + 9 語系（en、zh-Hant-TW、zh-Hans-CN、ko、ja、hi、es、pt-BR、ar） |
| `util/AppLocale.kt` | 記憶體快取語言 tag，`wrap(context)` 在 `attachBaseContext` 套用；App 啟動 `runBlocking` 從 Room 讀 |
| `DeveloperSettingsSection` | Template Builder toggle + 已存 template 下拉與刪除、Upload Template Builder、Review Templates、「顯示隱藏 DIY」、花朵餘額 ±1（flag） |
| `AboutScreen.kt`（`AboutUs`） | 全黑卡片 + 版權字串，點擊返回；由 drawer 進入 |
| `AIScreen.kt` | 只有一個顯示傳入字串的 `Text`。待確認：未見任何 route 使用，疑為佔位／殘留 |

## 7. 圖片載入與快取

- **單一 Coil `ImageLoader`**（`PaletteWallApplication.newImageLoader()`）：記憶體 25%、磁碟 2%，註冊 `ImageDecoderDecoder`（API 28+，含 animated WebP）或 `GifDecoder`；取代過去各元件各自 15% 的 loader。
- `ProgressiveImageLoaderSimple.kt`（`ProgressiveImageLoaderBest`）：靜態 placeholder → 模糊預覽（`thumbnailBlurUrl` 類）→ 完整圖 `AsyncImage`；完整圖畫出後是不透明的，placeholder 層不再重繪；避免 `SubcomposeAsyncImage` 的 subcomposition 成本；不用無限 shimmer（每張可見卡都跑動畫太耗）。
- APK 內建快取：`assets/cached_images/{LD,HD,BL,...}/images_{quality}_{filename}` 由 `ImageCacheList.fromAssets()` 掃描（`ImageCacheDataSource`），`ImagesCache.kt` 的 `String.getImageSourceFromAssets()` 把 URL 對應到 asset 路徑；`ImageCacheList.pathAfterImages()` 同時支援舊 Firebase URL-encoded 與新 CDN（`cdn.palettex.ca`）格式，有單元測試。
- `ImageFormatUtils.detectImageExt(uri)`：依 MIME / 檔名推副檔名（DIY 使用者圖片複製時用）。
- `DiyThumbnailCache.kt`：DIY 縮圖解析優先序與 `persistThumbnailFromDiskCache()`（Coil 下載成功後複製到 `filesDir/diy_thumbnails/`，避免冷啟動再下載）。
- 2026-07-13 R2 遷移：Material3Carousel 的 5 個寫死 Firebase URL 改 CDN；`firebase-storage-ktx` 已移除。

## 8. Analytics（瀏覽相關）

`page_view_live / static / collections / settings`（BottomBarBox）、`firebaseCatalogEvent`、`firebaseDownloadFreeEvent`、`firebaseShareEvent`、`firebaseLikeEvent`、`hero_thumbnail_click`、`home_feedback_*`、`feedback_*_clicked`；另有 `POST items/log` 的後端事件（`sendLogEvent`）。

## 9. 已知陷阱

- `LazyColumn` 內 DIY 分類務必逐 item 發出，否則動畫縮圖全部同時解碼。
- 自動輪播 effect key 要用 `settledPage`，不是 `currentPage`。
- `AnimatedImageDrawable` 不要 unregister callback（框架 race NPE，下拉更新時曾 crash）。
- in-app 語言：任何依語言的計算讀 `LocalConfiguration.current.locales[0]`，不要 `Locale.getDefault()`。
- 收藏頁購買價格只是資訊性顯示，結帳時 Billing 重查，不必進頁強制刷新。
