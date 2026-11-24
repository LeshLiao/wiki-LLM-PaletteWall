---
title: PaletteWallAndroid — 資料模型（Room、SharedPrefs、DTO、快取）
source: raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/data/local, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/data/remote/dto, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/service/DiyWallpaperConfig.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/screens/diy/DiySaveSerializer.kt, raw/PaletteWallAndroid/doc/diy_live_wallpaper_data_flow.md, raw/PaletteWallAndroid/CLAUDE.md
updated: 2026-11-24
confidence: high
---

# 資料模型

本頁整理 App 端所有持久化資料：Room 資料庫、SharedPreferences、遠端 DTO 與 domain model 的對應、DIY template 的序列化規則、以及圖片快取層。API 端點本身見 [[projects/PaletteWallAndroid/api]]，分層與資料流見 [[projects/PaletteWallAndroid/architecture]]，DIY 編輯 → Service 渲染的完整流程見 [[projects/PaletteWallAndroid/modules/diy-live-wallpaper]]。

## 1. Room：`WallpaperDatabase`

- 檔案：`app/src/main/java/com/palettex/palettewall/data/local/database/WallpaperDatabase.kt`
- DB 名稱 `wallpaper_database`，**version 10**，`exportSchema = false`
- 取得方式：`WallpaperDatabase.getDatabase(context)` 手動單例（**不經 Hilt**），各 Screen / ViewModel 直接呼叫對應 DAO
- `fallbackToDestructiveMigration()` 開著：找不到 migration 路徑就清庫重建

### 1a. 七張 table

| Table | Entity | 主鍵 | 欄位 | 用途 |
|---|---|---|---|---|
| `liked_wallpapers` | `LikedWallpaper` | `wallpaperId: String` | `imageUrl`、`timestamp` | 靜態桌布收藏（Fullscreen / Filter / Collection 頁） |
| `liked_diy_wallpapers` | `LikedDiyWallpaper` | `itemId: String` | `timestamp` | DIY 商品收藏 |
| `user_settings` | `UserSettings` | `id: Int = 1`（單列） | `isDarkThemeEnabled`（預設 true）、`languageTag: String?`、`themeId`（預設 `midnight_gold`） | 主題、語言；`PaletteWallApplication` 啟動時讀 `languageTag` 套 locale |
| `diy_save_template` | `DiySaveTemplate` | `id` 自增；`itemId` **unique index** | `itemId`、`name`、`createdAt`、`userImagesJson`、`transformsJson`、`backgroundJson`、`stickersJson`、`animationTextsJson`、`userTextsJson` | 使用者在編輯器對某個 DIY item 的編輯草稿（每 item 一份） |
| `dev_saved_template` | `DevSavedTemplate` | `id` 自增 | `name`、`createdAt`、`updatedAt`、`cardsJson`、`backgroundColorArgb: Long?`、`decorationsJson`、`backgroundJson`、`animationTextsJson`、`vignetteJson`、`previewTimeColorArgb: Int?`、`customTimeText`、`customDateText`、`previewTimeColorId` | Dev Template Builder 的本機草稿（debug 專用） |
| `diy_unlock_record` | `DiyUnlockRecord` | `itemId: String` | `unlockedAt`、`expiresAt`（epoch ms；**0 = 永久/已購買**） | DIY item 的解鎖/試用紀錄 |
| `flower_basket` | `FlowerBasket` | `id: Int = 1`（單列） | `balance`（0..24）、`streakDay`（1/2/3）、`lastClaimEpochDay`、`welcomeSeen`、`lastBloomAt`、`rewardedVersionCode`（-1 = 未領） | 花朵收集系統（簽到、每日 bloom、安裝/更新獎勵） |

### 1b. 關聯

Room 裡**沒有宣告 foreign key**，關聯全靠字串 id：

- `liked_diy_wallpapers.itemId`、`diy_save_template.itemId`、`diy_unlock_record.itemId` 都指向後端 `live_items` 的 `itemId`（同時也是 Google Play productId）。三張表以 `itemId` 一對一對齊，但各自獨立：刪草稿（`DiySaveTemplateDao.deleteByItemId`）時程式會一併 `DiyUnlockRecordDao.deleteByItemId` 撤銷試用（註解：下次要再看廣告）。
- `liked_wallpapers.wallpaperId` 指向靜態桌布的 `WallpaperItem.itemId`（待確認：是 `id` 還是 `itemId`，entity 命名為 `wallpaperId`）。
- `user_settings` 與 `flower_basket` 都是單列表，刻意分開：settings 的寫入是整列 REPLACE（讀→改→寫），會和 basket 依賴的原子 UPDATE 互相競爭。

### 1c. DAO 提供的操作

| DAO | 操作 | 備註 |
|---|---|---|
| `LikedWallpaperDao` | `insertLikedWallpaper`(REPLACE)、`deleteLikedWallpaper`、`getAllLikedWallpapers(): Flow`（timestamp DESC）、`isWallpaperLiked(id): Flow<Boolean>` | |
| `LikedDiyWallpaperDao` | `insert`、`delete`、`getAll(): Flow`、`isLiked(itemId): Flow<Boolean>` | |
| `UserSettingsDao` | `updateSettings`(REPLACE 整列)、`getSettings(): Flow`、`isDarkThemeEnabled()`、`getLanguageTag()`、`getThemeId()`（皆 Flow） | `SettingsViewModel` 寫、`PaletteWallApplication` / 主題層讀 |
| `DiySaveTemplateDao` | `upsert`、`getByItemId`、`getAllSavedItemIds(): Flow<List<String>>`、`deleteByItemId` | `EditDiyLiveWallpaperScreen` 讀寫；`LikeCollectionScreen`、`HeroQuickApply` 讀 |
| `DevSavedTemplateDao` | `upsert(): Long`、`getAll(): Flow`（updatedAt DESC）、`getById`、`getByName`、`deleteById` | `DevTemplateBuilderScreen`、`UploadTemplateBuilderScreen`、`DeveloperSettingsSection` |
| `DiyUnlockRecordDao` | `upsert`、`getByItemId`、`getAllFlow()`（Collection 頁倒數條）、`getAll()`（WorkManager 單次讀）、`deleteByItemId` | 寫入者：`DiyLiveModal`（看完廣告）、`LikeCollectionScreen`（免費續期）、`BillingViewModel`（購買 → `expiresAt = 0`） |
| `FlowerBasketDao` | `getBasket(): Flow`、`ensureRow()`、`claim(amount, nextStreakDay, today): Int`、`bloomClaim(now): Int`、`grantVersionReward(amount, versionCode): Int`、`spend(cost): Int`、`markWelcomeSeen()`、`devAdjustBalance(delta)` | 所有異動都是**單句 UPDATE + WHERE 守衛**，回傳受影響列數（0 = 被拒）：同日重複簽到、時鐘回撥、雙擊連點、餘額不足都在 SQL 層擋掉；balance 以 `MIN(..., 24)` 夾住 |

`FlowerBasketDao.ensureRow()` 必須列出每個 NOT NULL 欄位——新安裝時 Room 依 entity 建表、沒有 SQL default，`INSERT OR IGNORE` 遇 NOT NULL violation 會靜默丟棄。

### 1d. Migration 歷史

| 版本 | 內容 |
|---|---|
| 1 → 2 | **沒有定義 migration**（待確認：v1/v2 的差異已不可考，靠 destructive fallback） |
| 2 → 3 | 建 `liked_diy_wallpapers`、`diy_save_template`（含 unique index）、`dev_saved_template`；同一支 migration 內又 `ALTER` 加 `diy_save_template.animationTextsJson` 與 `dev_saved_template` 的 `previewTimeColorArgb` / `customTimeText` / `customDateText` / `previewTimeColorId` / `vignetteColorId` |
| 3 → 4 | `diy_save_template` 加 `userTextsJson`（default `'[]'`） |
| 4 → 5 | 重建 `dev_saved_template` 以**移除** `vignetteColorId`（同值已在 `vignetteJson` 內）；SQLite 不支援 DROP COLUMN，所以走 create new → INSERT SELECT → DROP → RENAME |
| 5 → 6 | `user_settings` 加 `languageTag` |
| 6 → 7 | `user_settings` 加 `themeId`（default `'midnight_gold'`） |
| 7 → 8 | 建 `diy_unlock_record`、`flower_basket`，並為升級用戶插入 basket 初始列（`welcomeSeen = 0` 讓他們看一次 Welcome） |
| 8 → 9 | `flower_basket` 加 `lastBloomAt`（default 0 = 立刻可領） |
| 9 → 10 | `flower_basket` 加 `rewardedVersionCode`（default -1 = 未領） |

每次在 `EditDiyLiveWallpaperScreen` 新增可編輯狀態，依來源 CLAUDE.md Rule 3 必須同步：`DiySaveTemplate` column → `DiySaveSerializer` → migration → `doSaveAndApply()` 寫入 → `LaunchedEffect` 載入 → `committed*` baseline + `hasEdits`。

## 2. SharedPreferences 清單

| Prefs 檔名 | Helper | Key | 存什麼 | 誰寫 | 誰讀 |
|---|---|---|---|---|---|
| `diy_wallpaper` | `service/DiyWallpaperConfig.kt` | `item_id`、`save_version`、`expires_at`、`template_json`、`user_image_{cardId}`、`transform_{scale/rotation/offset_x/offset_y/flip_h/flip_v}_{cardId}`、`bg_type`/`bg_color_argb`/`bg_image_uri`、`sticker_count` + `sticker_{id/emoji/start_x/start_y/end_x/end_y/size/rotation/scale/duration}_{i}`、`anim_texts_json`、`user_texts_json` | **目前套用中的 live wallpaper 全部狀態**，是 `DiyLiveWallpaperService` 唯一的資料來源 | `EditDiyLiveWallpaperScreen.doSaveAndApply()`（`save()`，一次寫全）、`LikeCollectionScreen` 續期（`updateExpiresAt()`，只在該 item 正套用時） | `DiyLiveWallpaperService`（`load*()`） |
| `diy_onboarding` | `ui/screens/diy/DiyCoachmarkPrefs.kt` | `coachmark_photos_seen` | 編輯器首次教學是否看過 | 編輯器關閉 coachmark 時 | `EditDiyLiveWallpaperScreen` |
| `feedback_prefs` | `util/FeedbackPrefs.kt` | `device_id`（隨機 UUID，非身分）、`suggestion_last_at` / `suggestion_version_code`、`bug_window_start_at` / `bug_count_in_window` / `bug_version_code`、`home_feedback_prompt_interacted` | 回饋功能的防灌水：建議 7 天一次、bug 回報 7 天內最多 3 次，換版本重置 | `FeedbackViewModel` | 同左 + 首頁回饋提示 |
| `trial_reminder` | `util/TrialReminderPrefs.kt` | `enabled`（預設 false） | 「到期前 3 天提醒」開關，開了才排 WorkManager | Collection 頁 toggle | `TrialExpiryReminderScheduler` |
| `trusted_time` | `util/TrustedTime.kt` | `anchor_server_ms`、`anchor_elapsed_ms` | 以 `AppSettings.serverTimeUtcMs` + `elapsedRealtime()` 錨定的伺服器時間，只拿來算「今天星期幾」（每週限免）；重開機後失效 → 回 0 → 限免 fail-closed | `HomeViewModel.getAppSettings()` | `HomeViewModel`、`DiyWallpaperItem.isFreeNow()` |
| `debug_analytics_toggle` | `util/DebugAnalyticsToggle.kt` | `analytics_disabled` | 隱藏開關：Settings 點版本號 10 次關閉 Firebase Analytics | Settings | App 啟動 `applyPersistedState()` |
| `welcome_prefs` | 直接在 `HomeScreen.kt` | `welcome_seen` | 首頁歡迎 overlay | HomeScreen | HomeScreen |
| `dev_prefs` | 直接在 `DeveloperSettingsSection.kt` | `dev_template_builder`、`dev_show_hidden_diy` | debug 開發者選項 | Settings → Developer | `HomeViewModel`（顯示 `isVisible = false` 的 DIY item） |
| In-app review / 通知前置提示 | `ui/components/InAppReview.kt`、`NotificationOptIn.kt` | 上次顯示時間、是否已問過 | 節流 Play In-App Review；通知權限只問一次 | 各自元件 | 同左 |

`UserSettings`（主題 / 語言）**不在** SharedPrefs，在 Room `user_settings`。

`DiyWallpaperConfig.save()` 必須用 `commit()`（同步）而非 `apply()`，否則 Service 可能在落盤前讀到空資料、首次設定畫面空白（來源 CLAUDE.md Rule 5）。`template_json` 只在 Save & Apply 時刷新：之後後端 template 改了，live wallpaper 仍渲染舊快照直到使用者重存（「Template 快照機制」）。`expires_at` 刻意**不放進** `template_json`——它是從 `DiyUnlockRecord` 導出的權益值，不是 template 內容（Rule 8）。

## 3. 遠端 DTO 與 domain model

### 3a. 靜態桌布

| 遠端 DTO（`data/remote/dto/`） | Domain（`domain/model/`） | 轉換 |
|---|---|---|
| `WallpaperDto{id, itemId, name, price, freeDownload, stars, photoType, tags, thumbnail, preview, imageList: List<ImageItemDto>, downloadList: List<DownloadItemDto>, createdAt, updatedAt, version}` | `WallpaperItem`（同欄位 + `sizeOptions: List<String>`） | `WallpaperDtoMapper.kt`：`WallpaperDto.toDomain()` 逐欄複製，並以 `imageList.map { it.resolution }` 算出 `sizeOptions` |
| `ImageItemDto{type, resolution, link, blob}` | `ImageItem` | 逐欄複製 |
| `DownloadItemDto{size, ext, link}` | `DownloadItem` | 逐欄複製 |
| `PaginatedResponse{items: List<WallpaperItem>, currentPage, totalPages, totalItems, hasMore}` | 直接是 domain | 無 mapper |
| `CatalogItem{id, key, title, photoUrl, width, height}`、`BoardItem{id, key, title, action, value, photoUrl, ratioWidth, ratioHeight}` | 直接給 UI 用 | 無 |
| `AppSettings{version, adsLevel, live_catalog: List<DiyCatalogEntry{key, names: Map<locale, title>}>, latestVersionCode, latestVersionName?, minVersionCode, serverTimeUtcMs, heroItemId?}` | 直接給 ViewModel | 無 |
| `LogEventRequest{itemId, appVersion, eventType, manufacturer, model, release, sdk, country}`、`FeedbackRequest{type, category, message, name, email, screenshots, deviceId, appVersion, versionCode, manufacturer, model, release, sdk, localeCountry, language}` | 上行 body | 無 |

待確認：只有 `items/search` 經過 mapper；`items/photoType/static`、`popular`、`page` 都由 Gson **直接反序列化成 `WallpaperItem`**，`sizeOptions` 這個 domain 欄位在 JSON 裡不存在，Gson 會塞 null 進非 null 型別——若有程式碼讀 `sizeOptions` 可能 NPE，需要查 UI 端用法。`CatalogConfig`（`titleRes`、`key`、`tag`）雖放在 dto 目錄但是 App 內寫死的分類設定，不是後端回傳。

`blob` 欄位（`ImageItemDto.blob`、`DiyAssetDto.blob`、`thumbnailBlob`）是去掉網域的純物件路徑（如 `images/LD/xxx.jpg`），R2 遷移時靠它重組 CDN URL。

### 3b. DIY

| 遠端 DTO | Domain / UI model | 轉換位置 |
|---|---|---|
| `DiyAssetsResponseDto{frames, samples, decorations, backgrounds, stickers: List<DiyAssetDto{id, url, blob, ext, isVisible?}>, colors: List<DiyColorAssetDto{id, hex}>}` | `DiyAssetsResponse` / `DiyAsset` / `DiyColorAsset`（`domain/model/DiyAsset.kt`） | `WallpaperRepositoryImpl.getDiyAssets()` 手動 map，`isVisible ?: true`；結果餵進 `DiyAssetModule.initialize()` 成全域查表（id → url/ext、colorId → Compose `Color`） |
| `DiyWallpaperItemDto{itemId, name, freeDownload, freeOnDaysOfWeek?, flowerCost, freeTrialDays, maxTrialDays, isVisible, tags, thumbnailUrl, thumbnailBlurUrl?, template: DiyTemplateJson?}` | `DiyWallpaperItem`（`ui/screens/diy/DiyLiveTemplate.kt`；商品元資料） | `HomeViewModel.loadDiyLiveWallpapers()` 手動 map：`freeOnDaysOfWeek ?: emptyList()`、`maxTrialDays <= 0 → 30`、`thumbnailBlurUrl ?: ""`、`template?.toDomain() ?: DiyTemplate(photoCards = emptyList())`；非 debug 時過濾 `isVisible = false` |
| `DiyTemplateJson` 及其子物件 `PhotoCardConfigJson` / `DecorationConfigJson` / `StickerConfigJson` / `TextConfigJson` / `VignetteConfigJson` / `AnimPhase2Json` / `CardPositionJson` | `DiyTemplate` / `PhotoCardConfig` / `DecorationConfig` / `StickerConfig` / `TextConfig` / `VignetteConfig` / `AnimPhase2` / `CardPosition`（渲染設定） | `UploadDiyTemplateRequest.kt` 內的 `toDomain()`（下行）與 `toJson()` / `toUploadJson()`（上行） |
| `DiyReviewItemDto`、`UploadDiyTemplateRequest`、`DevUploadUrlRequest/Response`、`FeedbackUploadUrlRequest/Response` | dev / admin 專用，見 [[projects/PaletteWallAndroid/api]] | — |

`DiyTemplate` 與 `DiyWallpaperItem` 的職責分離（Rule 8）：`DiyTemplate` 只有動畫 / 渲染設定；`itemId`、`name`、`freeDownload`、`tags`、`flowerCost`、`freeTrialDays` 等商品元資料在 `DiyWallpaperItem`，且**不存 price**——售價一律即時從 Google Play Billing 查。

## 4. DiyTemplate 序列化規則

來源：CLAUDE.md Critical Rules 第 3、4 條，與 `doc/diy_live_wallpaper_data_flow.md`。同一份 `DiyTemplateJson` 格式同時用於三個地方：上傳 API body、後端回傳、`SharedPrefs["template_json"]` 快照，所以向後相容是硬規則。

1. **Asset / drawable 以 name 字串存**（如 `"diy_frame_0001"`、`"drawable:diy_sample_0021"`），絕不存 raw resource id（每次 build 會變）。`DiyAssetModule.getAssetUrl()` 接受帶或不帶 `drawable:` 前綴；`DiyBackground.DrawableRes` 經 `DiyBackgroundRegistry.resIdToName()` / `nameToResId()` 來回。
2. **Enum 以字串存**（`clipShape = "RECTANGLE"`、`layer = "ABOVE_CARDS"`、`defaultFont = "DEFAULT"`、`animationType = "MOVING_UP"`、`effect = "STATIC"`），反序列化一律 `runCatching { X.valueOf(s) }.getOrDefault(預設)`，未知值安全回退。
3. **顏色以 `"#AARRGGBB"` 字串存**（`Integer.toHexString(argb).padStart(8,'0')` 大寫），讀回用 `android.graphics.Color.parseColor()`，失敗回黑色。顏色欄位是**雙軌**：`colorId`（API 色票 id，編輯器用）與 hex（`defaultColor` / `color` / `backgroundColor` / `previewTimeColor`，Service 用）並存，因為 Service 不能依賴 `DiyAssetModule`（Rule 5）；`DiyWallpaperConfig.save()` 遇 `DiyBackground.ApiColor` 會在存檔當下解析成 ARGB。
4. **新欄位必須有 default**，而且要考慮 Gson 繞過 Kotlin default 的行為：`List` 缺欄位 → null（用 `orEmpty()`）、`Float` → 0f（`startScale == 0f → 1f`、`clipDiagonalFraction == 0f → 1f`）、`Int` → 0（`AnimPhase2.durationMs <= 0 → 1000`，避免除以零）、`phase2` 整個缺 → null = 沒有第二段動畫。
5. **Room 內的 DIY 編輯草稿**（`DiySaveSerializer.kt`）格式與 API JSON 不同：`userImagesJson` 是 `Map<cardId, uriString>`、`transformsJson` 是 `Map<cardId, PhotoTransform>`、`stickersJson` 直接 Gson `StickerConfig`、`backgroundJson` 是前綴字串（`none` / `color:{argb}` / `image:{uri}` / `drawable:{name}` / `asset:{id}` / `apicolor:{colorId}`）、`animationTextsJson` / `userTextsJson` 走私有 `TextDto`（同時寫 `defaultColorArgb` 與 `defaultColorId`，舊資料只有 argb 也能讀）。所有 `deserialize*` 失敗一律回空值，不 throw。
6. 欄位流向檢查表（`doc/diy_live_wallpaper_data_flow.md`）逐欄追蹤 Dev Editor → Dev DB → Domain → API JSON → Canvas/Service → Duplicate-to-DB，目前所有欄位（含 QUAD 四角、phase2）皆完整；`template.stickers` 是 schema 支援但 Template Builder 無 UI 的前向相容欄位。改 config/DTO 欄位後要跑 `diy-template-reviewer` agent 更新該表。

使用者挑選的照片在挑選當下就由 `DiyImageStorage.copyToInternal()` 複製到 `filesDir/diy_user_images/{itemId}_{cardId}_{ts}.{ext}`，state 與 prefs 存穩定的 `file://` URI（Rule 6：絕不用 `takePersistableUriPermission`）。

## 5. 圖片快取層

| 層 | 檔案 | 機制 |
|---|---|---|
| APK 內建靜態桌布快取 | `data/local/model/ImageCacheList.kt`、`data/local/datasource/ImageCacheDataSource.kt`、`ui/components/utils/ImagesCache.kt` | 啟動時掃 `assets/cached_images/{LD,HD,BL,...}/`，建 quality → 檔名清單。`String.getImageSourceFromAssets()` 把桌布 URL 轉成 `images_{quality}_{filename}` 去比對，命中就回 `file:///android_asset/...` 給 Coil，否則回原 URL。`pathAfterImages()` 同時支援 Firebase 格式（`%2F` 編碼）與 R2 CDN 格式（純路徑）——R2 遷移時若沒改這裡，內建快取全失效、流量反而暴增。`ImageCacheDataSource` 由 `DataModule` 注入 repository，`getImageCacheList()` 暴露給 UI。 |
| DIY 縮圖 | `ui/components/utils/DiyThumbnailCache.kt` | `rememberDiyThumbnailModel()` 依序找：drawable `diy_thumbnail_{itemId}` → APK asset `cached_images/diy/thumbnails/` → `filesDir/diy_thumbnails/{itemId}.{ext}` → 網路 URL（交給 Coil）。首次網路載入成功後 `persistThumbnailFromDiskCache()` 從 Coil disk cache 複製一份到 `filesDir`，不重新下載；快取檔只在 mount 時檢查一次，避免動畫縮圖中途重載。副檔名優先序依 API level（28+ 偏好動態 webp，舊機偏好 gif）。`rememberDiyThumbnailBlurModel()` 對模糊佔位圖做同樣三層（asset → `{itemId}_blur.jpg` → URL），下載走 temp + atomic rename。 |
| DIY 素材 | `domain/usecase/PreloadDiyAssetsUseCase.kt` | 進編輯器前把 template 用到的 background / sample / frame / decoration 下載到 `filesDir/diy_assets/{id}.{ext}`，4 路並行、每檔 15 秒 timeout、temp + rename 保證存在即完整，`.tmp_` 超過 1 小時的殘檔啟動時清掉；`allCached()` 判斷是否可跳過。Service 只讀這個目錄，不碰網路。 |
| 使用者照片 | `ui/screens/diy/DiyImageStorage.kt` | 見第 4 節；`detectImageExt()`（`ImageFormatUtils.kt`）以 magic bytes 判 png/gif/webp/jpg。 |

## 6. 相關頁

- [[projects/PaletteWallAndroid/api]] — 端點、驗證、網路層
- [[projects/PaletteWallAndroid/architecture]] — Clean Architecture 分層、DI、導航
- [[projects/PaletteWallAndroid/modules/diy-live-wallpaper]] — DIY 編輯器 → SharedPrefs → WallpaperService 的完整流程
