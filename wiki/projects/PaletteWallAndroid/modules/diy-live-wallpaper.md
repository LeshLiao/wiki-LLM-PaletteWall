---
title: DIY Live Wallpaper（動態桌布編輯器與 WallpaperService）
source: raw/PaletteWallAndroid/CLAUDE.md, raw/PaletteWallAndroid/doc/diy/, raw/PaletteWallAndroid/doc/diy_live_wallpaper_workflow.md, raw/PaletteWallAndroid/doc/diy_live_wallpaper_data_flow.md, raw/PaletteWallAndroid/doc/e2_hero_quick_apply_plan_2026-07-23.md, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/service/, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/screens/diy/, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/screens/dev/
updated: 2026-11-24
confidence: high
---

# DIY Live Wallpaper

PaletteWall 的主力功能：使用者挑選一個由後端提供的 **template**（版面＋動畫設定），放入自己的照片、貼紙、文字、背景，預覽後一鍵設成 Android 動態桌布。渲染端是獨立的 `DiyLiveWallpaperService`（WallpaperService），完全離線、只讀 SharedPrefs 快照。

相關頁：[[projects/PaletteWallAndroid/architecture]]（分層與 DI）、[[projects/PaletteWallAndroid/data-model]]（Room / SharedPrefs / DTO 欄位）、[[projects/PaletteWallAndroid/api]]（`/api/live_items`、`/api/assets`）、[[projects/PaletteWallAndroid/modules/monetization]]（購買 / 廣告解鎖）、[[projects/PaletteWallAndroid/modules/retention-and-trial]]（免費 trial 與到期 overlay）、[[projects/PaletteWallAndroid/modules/home-and-browsing]]（首頁 DIY 區塊與 Hero）。

## 1. 端到端流程

```
[Dev] DevTemplateBuilderScreen 編輯 template
   → Room dev_saved_template（DevSavedTemplate）
   → UploadTemplateBuilderScreen：thumbnail 上傳 R2（presigned URL）+ POST /api/live_items
        （或 AI skill → POST /api/diy_review 暫存 → ReviewTemplatePageScreen 人工審核 → 後端手動 promote）
[App] HomeViewModel.loadDiyLiveWallpapers()：GET /api/live_items → DiyWallpaperItemDto.template.toDomain()
      HomeViewModel.loadDiyAssets()：GET /api/assets → DiyAssetModule.initialize()
   → 首頁 GridDiyLiveWallpaper / HeroQuickApplySection 顯示縮圖
[User] 點卡片 → edit_diy_live_wallpaper/{itemId}?fromCollections=
   → PreloadDiyAssetsUseCase 先把 template 用到的 assets 下載進 filesDir/diy_assets/（DiyAssetLoadingOverlay 進度條）
   → EditDiyLiveWallpaperScreen 編輯（photo / background / sticker / text / animation text）
   → Preview（WallpaperCanvas 在 App 內播動畫）
   → Save：gating（已購買 / trial / 免費看廣告 / 購買 modal）
   → doSaveAndApply()：Room diy_save_template（草稿）+ SharedPrefs diy_wallpaper 快照（含 template_json）
   → ACTION_CHANGE_LIVE_WALLPAPER 系統預覽頁 → 使用者按「設定桌布」
[Service] DiyLiveWallpaperService.onVisibilityChanged → 比對 save_version → loadBitmaps() → Choreographer draw loop
```

完整流程圖在來源 `doc/diy_live_wallpaper_workflow.md`；每個欄位在哪個階段存在／被丟棄的對照表在 `doc/diy_live_wallpaper_data_flow.md`（由 `diy-template-reviewer` agent 維護）。

## 2. 主要檔案與職責

| 層 | 檔案（相對 `app/src/main/java/com/palettex/palettewall/`） | 職責 |
|---|---|---|
| 資料模型 | `ui/screens/diy/DiyLiveTemplate.kt` | `DiyTemplate`、`DiyWallpaperItem`、`PhotoCardConfig`、`DecorationConfig`、`StickerConfig`、`TextConfig`、`AnimPhase2`、`PhotoClipPreset`、`DiyBackground`、`DiyEditorMode`、`isFreeNow()`、`rest*` extensions；末端 `DiyTemplateRegistry` 已停用 |
| DTO | `data/remote/dto/UploadDiyTemplateRequest.kt` | `DiyTemplateJson` 及 `toUploadJson()` / `toDomain()` 雙向轉換（顏色存 `#AARRGGBB` 字串） |
| 編輯器 | `ui/screens/diy/EditDiyLiveWallpaperScreen.kt` | Orchestrator：state、modes、gating、Save、Exit dialog（約 1600 行） |
| 畫布 | `ui/screens/diy/WallpaperCanvas.kt` | Compose 預覽畫布，per-element `Animatable` |
| Edit bars | `TemplateEditBar.kt`、`PhotoEditBar.kt`、`BackgroundEditBar.kt`、`StickerEditBar.kt`、`TextEditBar.kt`（`AnimationTextEditBar.kt` 為薄包裝）、`UserTextAddBar.kt` | 各模式底部工具列 |
| 儲存 | `ui/screens/diy/DiySaveSerializer.kt`、`data/local/entity/DiySaveTemplate.kt`、`data/local/dao/DiySaveTemplateDao.kt` | 草稿 JSON 序列化與 Room upsert-by-itemId |
| 快照 | `service/DiyWallpaperConfig.kt` | SharedPrefs `diy_wallpaper`：Service 唯一的資料來源 |
| 渲染 | `service/DiyLiveWallpaperService.kt` | WallpaperService + Engine、draw loop、到期 overlay |
| 圖片 | `ui/screens/diy/DiyImageStorage.kt`、`ui/screens/diy/PhotoClipShapeUtils.kt` | 使用者圖片複製進內部儲存；Compose / Service 共用的 clip path |
| Assets | `domain/module/DiyAssetModule.kt`、`domain/usecase/PreloadDiyAssetsUseCase.kt`、`GetDiyAssetsUseCase.kt`、`GetDiyLiveWallpapersUseCase.kt` | 遠端 asset 查詢、預下載、template 列表 |
| Registry | `DiyFrameRegistry.kt`、`DiyBackgroundRegistry.kt`、`DiyDecorationRegistry.kt`、`DiySampleRegistry.kt` | APK drawable 名稱 ↔ resId（過渡期相容） |
| Hero | `ui/screens/diy/HeroQuickApply.kt`、`ui/screens/home/HeroQuickApplySection.kt` | 首頁一鍵套用 |
| Dev | `ui/screens/dev/*`、`ui/screens/diy/DebugDuplicateToTemplateBuilderDialog.kt` | Template builder / 上傳 / 審核工具 |
| Onboarding | `DiyCoachmarkOverlay.kt`、`DiyCoachmarkPrefs.kt`、`DiyAssetLoadingOverlay.kt` | 首次進編輯器提示、asset 下載進度 |

## 3. 資料模型要點（Rule 8：職責分離）

- **`DiyTemplate`** 只放渲染／動畫設定：`photoCards`、`stickers`、`decorations`、`animationTexts`、背景（`backgroundColor` / `backgroundColorId` / `backgroundAssetId`）、`previewTimeColor(Id)`、`vignette`、`customTimeText/DateText`。
- **`DiyWallpaperItem`** 放商品元資料：`itemId`（= Google Play productId）、`name`、`freeDownload`、`freeOnDaysOfWeek`、`flowerCost`、`freeTrialDays`、`maxTrialDays`、`tags`、`thumbnailUrl`、`thumbnailBlurUrl`、`isVisible`，以及 `template`。
- **不加 hardcode `price`**：售價一律即時從 Google Play Billing 查（`BillingViewModel.getOneTimePurchasePrice()`），見 [[projects/PaletteWallAndroid/modules/monetization]]。
- `expiresAt`（trial 到期）**不**進 template，走 SharedPrefs 獨立 key `expires_at`，來源是 Room `diy_unlock_record`。
- Asset 以 **id 字串**（如 `"diy_frame_0001"`）存，不存 resId；`"drawable:"` 前綴為 APK drawable 的過渡相容格式。
- Enum 以字串存，反序列化 `runCatching { valueOf() }.getOrDefault(...)`；新增欄位必須有 default（舊 SharedPrefs JSON 仍要能讀）。
- Gson 繞過 Kotlin constructor default：DTO 缺欄位會得到 `0`/`null`，所以 `durationMs <= 0 → 1000`、`clipDiagonalFraction 0 → 1`、`maxTrialDays <= 0 → 30` 這類修正都放在 mapping / `toDomain()`。

## 4. 座標與尺寸 fraction 系統（Rule 1）

`CardPosition(x, y)` 是 canvas 比例（0 = left/top，1 = right/bottom），position 是**卡片中心點**。
**卡片寬與高都是 canvas「寬度」的比例**（`widthFraction` / `heightFraction`），不是 dp：

```
offsetX = position.x × canvasWidthDp  - canvasWidthDp × widthFraction / 2
offsetY = position.y × canvasHeightDp - canvasWidthDp × heightFraction / 2
wPx = widthFraction  × canvasWidth    (Service 端，免 density 換算)
hPx = heightFraction × canvasWidth
```

**唯一的不對稱（最常見 bug 來源）：Height 是 canvas 寬度的比例，End_y 是 canvas 高度的比例。** Dev builder 的 Layout 面板上兩者並排，容易混淆。

參考換算（以 360dp 寬為基準）：100dp→0.278、150dp→0.417、90dp→0.250、80dp→0.222。`DecorationConfig.sizeFraction` 同樣相對 canvas 寬；`StickerConfig.sizeDp` 則仍是固定 dp（歷史例外）。`photoInsetTop/Bottom` 是 card 高度的比例，`photoInsetLeft/Right` 是 card 寬度的比例。

## 5. Compose 預覽與 Service 渲染如何保持一致（Rule 7）

| 面向 | WallpaperCanvas（Compose） | DiyLiveWallpaperService | 一致性要求 |
|---|---|---|---|
| 照片縮放 | `ContentScale.Fit`（`min(scaleX, scaleY)`） | `fitScaleBitmap()`（同 `min`） | 曾因 Service 用 `fillWidthScaleBitmap` 而不一致，已修正 |
| Decoration | `ContentScale.Fit` | `fitScaleBitmap(raw, sizePx, sizePx)` 等比置中於透明底 | 曾因 `createScaledBitmap` 拉伸成正方形而變寬，已修正 |
| Easing | `FastOutSlowInEasing` | `PathInterpolator(0.4f, 0f, 0.2f, 1f)` | 兩者相同曲線 |
| 動畫狀態 | 每元素 `Animatable`（position 用 `Animatable<Offset, AnimationVector2D>` + `Offset.VectorConverter`） | 每 frame 以 `elapsedMs` 插值，寫回 `tempPos: FloatArray(2)` | 都以 `startX/endX + durationMs + delayStartMs` 描述 |
| 靜止終態 | 非 PREVIEW 一律 `snapTo(rest*)` | `Phase.PAUSING` 分支用 `rest*` | 加了 phase2 後**不可再直接用 `end*`** |
| Clip shape | `photoClipShape(preset, f)` → Compose `Shape` | `buildCardClipPath()` → `android.graphics.Path`，在 `loadBitmaps()` 一次裁好 | 同一檔 `PhotoClipShapeUtils.kt` 共用公式 |
| 圓角 | `RoundedCornerShape` | `BitmapShader + drawRoundRect`（WallpaperService surface 上 `clipPath` 不可靠） | 視覺等價 |
| Frame | 疊圖 | 在 `loadBitmaps()` 預合成進照片 bitmap，draw loop 不再每 frame 混合 | Frame PNG 長寬比要等於 `widthFraction:heightFraction` |

Compose 端陷阱：`offset { }` lambda 是 `Density` scope，offset 以 dp 存、用 `.dp.roundToPx()` 轉；`LaunchedEffect(canvasWidthDp, canvasHeightDp)` 必須 guard `mode == PREVIEW`，否則進 PREVIEW 時 bars 消失造成 resize，`snapTo(endPosition)` 會取消進行中的動畫。

## 6. 動畫系統

### 6.1 第一階段屬性（`doc/diy/animation_system.md`）

`PhotoCardConfig` / `DecorationConfig` 共用模式：每個屬性都是 `startX / endX`，同一個 `durationMs` 控制，`delayStartMs` 延後起點。

| 屬性 | 欄位 | 備註 |
|---|---|---|
| 位置 | `startPosition` / `endPosition` | fraction |
| 旋轉 | `startRotation` / `endRotation` | Compose `graphicsLayer.rotationZ`；Service `canvas.rotate(r, cx, cy)` |
| 縮放 | `startScale` / `endScale` | |
| 透明度 | `startAlpha` / `endAlpha` | Service 設 `photoPaint.alpha` 後畫完 restore 255 |
| 延遲 | `delayStartMs` | `effectiveElapsed = (elapsed - delay).coerceAtLeast(0)` → 延遲期間停在 start |
| Decoration 圖層 | `layer = BELOW_CARDS / ABOVE_CARDS` | Compose 與 Service 都分兩段渲染 |
| 照片視窗 | `photoInset*` | Polaroid 白邊內的相片區 |
| 裁切 | `clipShape: PhotoClipPreset` + `clipDiagonalFraction` + `quad*` 八個角 | 三角形／平行四邊形／梯形／任意四邊形；互補三角形可拼成一張 |
| 影子 / 圓角 | `shadowRadius`、`fourCornerRadius` | |
| 圖片鏡像 | `copySameImageTo` | 來源卡挑圖與 transform **單向**同步到目標卡（`updateTransform()` 是唯一傳播點） |
| Placeholder | `placeholderColor` | 無使用者圖時畫的色塊 |

`maxDuration = max(photoCards.totalDurationMs(), decorations.totalDurationMs(), stickers.durationMs, animationTexts.delay+duration)`；Service 播完一次進 `PAUSING`。

Decoration 與 Sticker 的差別：Decoration 由 template 作者定義（PNG 透明背景，位置/旋轉/縮放動畫），使用者不可編輯；Sticker 是使用者放的 emoji（`startPosition == endPosition`，不動畫）。文字同理：`animationTexts` 是作者定義（可動），`userTexts` 是使用者加的靜態文字，兩者共用 `TextConfig` 與 `TextEditBar`，但 id 與 animatable map 各自獨立（sticker id 從 10000 起、userText 從 20000 起避免與 template 內 id 撞）。

### 6.2 第二階段動畫 Phase 2（`doc/diy/phase2_animation.md`，2026-08-06）

```kotlin
data class AnimPhase2(
    val endPosition: CardPosition? = null, // null = 該屬性第二階段不變
    val endRotation: Float? = null, val endScale: Float? = null, val endAlpha: Float? = null,
    val delayMs: Int = 0, val durationMs: Int = 1000,
)
```

- `PhotoCardConfig` / `DecorationConfig` 各有 `phase2: AnimPhase2? = null`；Sticker / Text 不支援。
- **Phase 2 起點永遠 = Phase 1 終點**（不存 start2，保證連續）。時間軸：`delayStartMs → durationMs → p2.delayMs（停在 end1）→ p2.durationMs → 靜止`。
- `restPosition/restRotation/restScale/restAlpha` extensions 與 `totalDurationMs()` 是樞紐：所有「靜止終態」一律用 `rest*`。
- Service 8 個 helper（`cardOffset/Rotation/Scale/Alpha`、`decoration*`）統一兩段插值，只有分支與整數運算、零 allocation。
- Compose 在 PREVIEW 的每個屬性 coroutine 於第一段 `animateTo` 完成後直接串接第二段。
- 向後相容：舊 JSON 缺 `phase2` → null → 行為不變；**舊版 App 收到含 phase2 的 template 只播第一段、停在 phase-1 終點**（構圖是中間態，需靠後端可見性控制擋舊版）。`DiySaveTemplate` 不需 migration（phase2 是作者屬性）。
- 已知限制：上傳工具產生的 blur 縮圖＝最後一格＝phase-2 終態，需確認縮圖產生器跑完整動畫。

## 7. 編輯器 EditDiyLiveWallpaperScreen（`doc/diy/editor.md`）

### 7.1 Modes（`DiyEditorMode`）

| Mode | 底部 bar | 畫布行為 |
|---|---|---|
| `TEMPLATE_EDIT` | Photos / Background / Sticker / Text（`TemplateEditBar`，icon 色跟 template datetime 色） | 卡片停在 rest 終態；頂部 back / Save（`DiyLiveWallpaperSaveButton`）/ Reset / 愛心 |
| `PHOTO_EDIT` | Single Replace / Batch Replace / Rotate / Flip / Zoom / Done | 選中卡片紅框（畫在最上層 overlay，不被 ABOVE_CARDS decoration 蓋住） |
| `BACKGROUND_EDIT` | 色票 + 圖片 picker / Done | 使用者背景蓋過 template 背景；選 None 則顯示 template 背景 |
| `STICKER_EDIT` | emoji LazyRow / Done | 單指移動、雙指縮放旋轉；邊框與刪除鈕用 `invScale` 維持固定視覺粗細 |
| `ANIMATION_TEXT_EDIT` / `USER_TEXT_EDIT` | Text / Size / Color / Font / Done（共用 `TextEditBar`） | 紅框 + 刪除 |
| `USER_TEXT_ADD` | `[Text here…] [Add]` | 點畫布取消 |
| `PREVIEW` | 隱藏 | `snapTo(start)` → 並行 `animateTo(end)` → `delay(2000)` 迴圈；疊 `DateTimeDisplay`；點擊回 TEMPLATE_EDIT |

Back 鍵：非 TEMPLATE_EDIT 模式先回 TEMPLATE_EDIT；TEMPLATE_EDIT 時 `hasEdits` 為真才彈 Exit dialog。

### 7.2 Save gating（`saveAndApplyWallpaper()`）

```
isPremium || isAlreadyPurchase            → doSaveAndApply()（expiresAt = 0）
isTrialItem && trial 生效中                → doSaveAndApply()（沿用既有 expiresAt）
isFreeNow（freeDownload 或今日限免）         → DiyLiveModal 看 Rewarded Ad → onEarned：
                                             freeTrialDays > 0 → upsert DiyUnlockRecord(now + days) → doSaveAndApply
                                             freeTrialDays == 0 → 永久
FLOWER_SYSTEM_ENABLED && isFlowerTrialItem → FlowerTrialModal（flag 目前關閉，跳過）
其餘                                       → showPurchaseModal（OneTimePurchaseModal）
```

每個分支記一個 `*_SaveAndApply` analytics 事件，3 秒內同名去重（GA4 曾觀察到連發 3–6 次）。詳細金流／廣告見 [[projects/PaletteWallAndroid/modules/monetization]]，trial 規則見 [[projects/PaletteWallAndroid/modules/retention-and-trial]]。

### 7.3 `doSaveAndApply()` 寫了什麼

1. `DiyWallpaperConfig.save(context, itemId, userImages, cardTransforms, background, stickers, animationTexts, userTexts, template, expiresAt)` → SharedPrefs，**內部 `commit()`**。
2. 條件允許時（premium / 已購買）另 upsert Room `diy_save_template` 草稿；`fromCollections=true` 時同步更新 committed baseline。
3. `launchLiveWallpaperPreview()`：`ACTION_CHANGE_LIVE_WALLPAPER`（帶 `EXTRA_LIVE_WALLPAPER_COMPONENT`）→ 失敗 fallback `ACTION_LIVE_WALLPAPER_CHOOSER` → 再失敗 Toast（事件 `diy_warning_device_chooser_fallback` / `diy_warning_device_not_supported`）。
4. 套用後回 App 的正向時刻：`NotificationOptIn.maybeRequest()` 或 `InAppReview.requestIfEligible()`。

| 條件 | SharedPrefs | Room 草稿 |
|---|---|---|
| premium / 已購買 | 寫 | 寫 |
| 免費 + 看完廣告 | 寫 | 不寫 |
| 未購買付費項目 | 不寫 | 不寫 |

### 7.4 Exit dialog 與 committed baseline

`hasEdits` 不是「狀態非空」，而是「與最後一次 committed 狀態不同」。六個 `committed*`：images / transforms / background / stickers / animationTexts / userTexts。baseline 在 DB 載入成功、以及 `fromCollections=true` 的 DB upsert 成功後更新；一般 Save（非收藏進入）不更新，退出仍會問。

### 7.5 Reset / 刪除草稿

- Reset（只在 `fromCollections && hasSavedConfig`）：`deleteByItemId` 後還原 template 預設。
- 刪除草稿（編輯器與收藏頁 SAVED 分頁）會**一併撤銷 trial 記錄**（`DiyUnlockRecordDao.deleteByItemId` + `TrialExpiryReminderScheduler.reschedule`），已套用中的桌布不受影響（Service 讀自己的快照）。

## 8. 使用者圖片：`DiyImageStorage.copyToInternal()`（Rule 6）

- 系統 Photo Picker 回傳的 `content://` URI 常常**沒有 persistable grant**：`takePersistableUriPermission` 會丟 `SecurityException`；就算沒丟，grant 也可能在 WallpaperService（獨立 process）讀之前被撤銷，卡片變空白。
- 解法：**挑選當下**（不是 Save 時）把 bytes 複製進 `filesDir/diy_user_images/{itemId}_{cardId}_{timestamp}.{ext}`，state 存 `file://` URI。三個 callback：`onImagePicked`（單張）、`onBatchImagesPicked`（批次）、`onBackgroundSelected`（`{itemId}_background`）。
- timestamp 後綴是為了讓 Coil 快取與 Compose 結構相等比較能分辨「重挑同一張卡」；舊檔先刪避免孤兒。GIF 不支援（`isGif()` 檢查）。
- Save 只是序列化既有 state（`uri.toString()` passthrough），SharedPrefs 與 Room 同時拿到穩定 URI。過渡期：舊草稿裡的 `content://` 不會自動重複製，只有重挑那張卡才會。
- 使用者刪掉相簿原圖、重開機都不影響；免儲存權限；清資料／解除安裝時一起消失。

## 9. WallpaperService（`doc/diy/wallpaper_service.md`）

### 9.1 獨立性（Rule 5）

- **絕不做網路請求**（尤其 draw loop）、**不使用** `DiyTemplateRegistry`、不打 API。
- Template 來源只有 SharedPrefs 快照：Save 時 `DiyTemplate.toUploadJson()` → `template_json`；Service `DiyWallpaperConfig.loadTemplate()` 讀回。後端 template 之後改了，桌布仍用舊快照直到重新 Save。
- `DiyWallpaperConfig.save()` / `updateExpiresAt()` 都用 **`commit()`**（同步）而非 `apply()`——否則 `startActivity()` 後 Service 可能在磁碟寫入前讀取，首次設定畫面空白（已踩過）。
- `ApiColor` 背景在 Save 時就解析成 ARGB 存入，Service 不呼叫 `DiyAssetModule`。
- `loadAssetBitmap()` 順序：`filesDir/diy_assets/{id}.{ext}` → APK drawable → URL 下載（後者只在冷啟動快取 miss 時發生，是 loadBitmaps 階段而非 draw loop；設計上 preload 已保證快取存在）。**ext-agnostic 掃描**：Service 冷啟動時 `DiyAssetModule` 未初始化，`inferExtFromId()` 猜 ext 會錯（正式站 samples 混 webp/jpg/png），所以精確檔名 miss 後接受 `{id}.*`。這是 2026-07-10 修掉「App 更新／重開機後 sample 與 background 消失」的根因。

### 9.2 Draw loop 鐵律（Rule 2）

```kotlin
private val frameCallback = object : Choreographer.FrameCallback {   // 必須是 object，lambda 無法自我引用
    override fun doFrame(frameTimeNanos: Long) {
        drawFrame(frameTimeNanos)
        if (isRunning && phase == Phase.ANIMATING) choreographer.postFrameCallback(this)
    }
}
```

- **draw 路徑禁止任何 allocation**（`Paint/Shader/Matrix/Bitmap/Pair...`）。需要的物件宣告成 Engine 欄位重用（`photoPaint`、`stickerPaint`、`shadowPaint` + `blurFilterCache`、`typefaceCache`、`tempPos: FloatArray(2)`），或在 `loadBitmaps()` 預算（vignette 四個 `LinearGradient`、過期 overlay 的 Paint 與 icon bitmap、frame 預合成）。位置用 `tempPos` 寫回，勿回傳 `Pair`。
- **動畫播完（`Phase.PAUSING`）後 loop 必須停止**：`doFrame` 只在 `ANIMATING` 時 re-post。實機（OPPO）量測：優化前每秒 ~120ms 主執行緒 CPU 永不下降，優化後 1 秒後降到 ~20ms/s。
- Phase 狀態機只有 `ANIMATING → PAUSING`。`onVisibilityChanged(false)`：重設 `ANIMATING`、畫一幀 start frame 讓系統存快照；`onVisibilityChanged(true)`：比對 `save_version` 決定 reload，重設 `ANIMATING` 重播一次。
- 時鐘全程 `System.nanoTime()`（`phaseStartNanos` 與 Choreographer 的 `frameTimeNanos` 同源）。早期混用 `currentTimeMillis` 曾壞過，勿再混。
- 使用者照片解碼上限 `PHOTO_MAX_DECODE_PX = 2048`，避免大圖 × zoom 爆記憶體。
- `releaseBitmaps()` 不呼叫 `recycle()`：bitmap 已交給 hardware canvas pin 成 texture，recycle 會造成 native crash（Play Console 可見、Crashlytics 看不到）；丟掉最後一個 reference 即可。

### 9.3 圖層順序（下→上）

0 黑色基底 → 1 template backgroundColor → 2 template backgroundImage → 3 使用者背景（SolidColor / Image；None 時透明）→ 4 Decorations BELOW_CARDS → 5 Photo cards（照片 + frame 預合成）→ 6 Decorations ABOVE_CARDS → 7 Stickers → 8 AnimText → 9 UserText → 10 DateTimeDisplay（只有編輯器 PREVIEW 畫）→ 11 編輯器選取框（Service 不畫）→ Vignette → 到期 scrim + 文字 + App icon（`isExpired` 時）。

### 9.4 到期 overlay

`loadBitmaps()` 讀 `loadExpiresAt()`；`checkExpiry()` 在每次 `onVisibilityChanged` 與 reload 後重算 `isExpired = expiresAt > 0 && now > expiresAt`（**裝置時鐘，刻意不防改時鐘**）；螢幕亮著時用 `expiryHandler.postDelayed` 準時變臉。到期時 `draw()` 強制 `PAUSING`、畫半透明 scrim + 「桌布已到期」+ 兩行提示 + 預烤圓角的 App icon。機制細節見 [[projects/PaletteWallAndroid/modules/retention-and-trial]]。

## 10. Remote template 架構與 Registry（`doc/diy/remote_template_architecture.md`）

- 目標：DIY 資源（frames / backgrounds / decorations / samples / stickers / colors）不打包進 APK，改由 `GET /api/assets` 取得 CDN URL（Cloudflare R2），快取至 `filesDir/diy_assets/{assetId}.{ext}`；template 由 `GET /api/live_items` 提供。
- `DiyAssetModule`（singleton）：`HomeViewModel.loadDiyAssets()` 後初始化，提供 `getAssetUrl()` / `getAssetExt()` / `colorIdToColor()` / `colorIdToColorOrNull()`（nullable 版是為了讓 datetime 顏色 fallback 鏈 `colorId → 存檔 hex → 白` 正確，否則未載入時會變黑）/ `getAllBackgrounds(onlyVisible)`。
- Asset id 格式：`diy_frame_*`、`diy_sample_*`、`diy_decoration_*`、`diy_background_*`、`diy_sticker_*`；`"drawable:xxx"` 前綴走 APK drawable。
- 四個 Registry（`DiyFrameRegistry` / `DiyBackgroundRegistry` / `DiyDecorationRegistry` / `DiySampleRegistry`）在 `PaletteWallApplication.onCreate()` 用反射掃 `R.drawable` 的 `diy_frame*` / `diy_background*` / `diy_decoration*` / `diy_sample*` 欄位，提供 `nameToResId()` / `resIdToName()`。序列化永遠存 name（resId 每次 build 會變）。
- 進度（來源文件表）：Phase 2（assetId 字串化）、3（進編輯器前預下載 + 進度條）、4（HomeViewModel 從 API 取 template，Registry 停用）已完成；Phase 5（上傳既有 drawable 至 R2、移除 APK 打包、刪 `DiyTemplateRegistry`）待做。待確認：表中 Phase 1「後端 API 待做」看起來已過時——changelog 2026-07 已在正式後端使用 `/api/live_items`、`/api/assets`。
- 首頁縮圖：`DiyThumbnailCache.rememberDiyThumbnailModel()` 優先序 drawable → APK bundled asset（`assets/cached_images/diy/thumbnails/`）→ `filesDir/diy_thumbnails/` → CDN URL；API 28+ 偏好 animated WebP，否則 GIF。DIY 區塊有獨立 `isDiyLoading`，不等靜態桌布 API。
- 首頁 DIY 分類：`buildDiyCategories(items, live_catalog, localeTags)` 依 `tags` 分組，順序與多語系標題來自 `AppSettings.live_catalog`（`DiyCatalogEntry(key, names)`），無 tag 進無標題的 others；locale 要讀 `LocalConfiguration.current.locales[0]`（反映 in-app 語言），不能用 `Locale.getDefault()`。另有置頂的「Free Today」群組與 Hero 區塊，見 [[projects/PaletteWallAndroid/modules/home-and-browsing]]。

## 11. Dev 工具（`doc/diy/dev_tools.md`）

入口：Settings → `DeveloperSettingsSection`（DEBUG build）→ Template Builder toggle、Upload Template Builder、Review Templates。

| 工具 | 檔案 | 用途 |
|---|---|---|
| Template Builder | `ui/screens/dev/DevTemplateBuilderScreen.kt`（~1100 行）、`DevCardPropertyPanel.kt`（~1700 行）、`DevTemplateState.kt`、`DevCardSnapshot.kt` | 視覺化編 template：Card / Deco / AnimText 面板，sub-tabs Layout（Width/Height `TextFieldSliderRow`、Start/End 四欄位、photoInset）、Corner（Radius、9 種 `PhotoClipPreset` chips、Diagonal、QUAD）、Phase2（紫色；Switch 開啟即以 phase-1 終值初始化全部欄位）；畫布可拖曳藍（start）/綠（end）/紫（end2）圓點；Preview 中改任何設定自動退出 Preview；新 template 的 datetime 色自動 commit 第一個 palette 色。存 Room `dev_saved_template`（`DevSavedTemplate`：cardsJson / decorationsJson / backgroundJson / animationTextsJson / vignetteJson / previewTimeColor* / customTime/DateText） |
| Kotlin 匯出 | `ui/screens/dev/DevKotlinExporter.kt` | 把 `DevTemplateState` 輸出成可貼進程式碼的 Kotlin（含 `appendPhase2()` 只在啟用時輸出、`backgroundImage = R.drawable.xxx`） |
| 上傳 | `ui/screens/dev/UploadTemplateBuilderScreen.kt` | 選已存 DevTemplate → 填 itemId（自動產生 `yyyyMMdd_HHmm_ss_xxxxxxxx` UTC）/ name / price / freeDownload / isVisible / tags → thumbnail 走 `POST /api/dev/upload-url` 取 presigned URL 後 PUT 到 R2（`live_templates/thumbnails/{itemId}.jpg`）→ `POST /api/live_items`。只有 thumbnail 是 per-template 上傳；其他 asset 引用 id。目前沒有 `flowerCost/freeTrialDays/freeOnDaysOfWeek/maxTrialDays` 的編輯 UI（後端管理） |
| 審核 | `ui/screens/dev/ReviewTemplatePageScreen.kt` | `GET /api/diy_review` 列出 AI skill 產生的暫存 template，用 `WallpaperCanvas` 實況預覽；點選以 `reviewItemId` 載入 Template Builder 編輯後 `POST /api/diy_review` 存回；promote 到 `live_items` 是後端手動步驟 |
| Duplicate to DB | `ui/screens/diy/DebugDuplicateToTemplateBuilderDialog.kt` | 編輯器（DEBUG）把目前載入的 API template 完整快照回 builder 的 Saved Templates（含 QUAD 與 phase2，2026-08-06 修掉漏 phase2） |
| 刪除 | `WallpaperApiService.deleteLiveItem` / `deleteDiyReviewItem` | API 方法已存在。待確認：來源文件寫「Delete Template 尚未實作」，但 `DeveloperSettingsSection` 有 Delete Template dialog（看起來是刪本地 dev DB），遠端刪除的 in-app 入口需再核對 |

Rewarded ad 的 `RewardedAdState` 與 `DiyLiveModal` loading 行為也在同份文件，整理於 [[projects/PaletteWallAndroid/modules/monetization]]。

## 12. Hero Quick Apply（E2，`doc/e2_hero_quick_apply_plan_2026-07-23.md`）

- 動機：63% 新用戶從未打開 DIY 編輯器、首日成功套用率 12.2%、首小時卸載 58%。套用＝留存分水嶺。
- v1（2026-07-15，每張 Free Today 縮圖上都有按鈕）已 revert；本版是**首屏獨立 Hero 區塊只放一支**。
- `HeroQuickApplySection`：左 40% 寬 9:20 動畫卡（`DiyLiveWallpaperCard`，`showFreeTag=false`）＋右側文案與 teal 漸層 CTA（與 StartedGuide CTA 同語言）。點縮圖→進編輯器（`hero_thumbnail_click`）；點 CTA→一鍵套用（`hero_quick_apply`）。
- 選品：`HomeScreen.HERO_ITEM_ID` 固定值，後端 `AppSettings.heroItemId` 非空時優先（遠端輪替／關閉；item 不在 catalog 就整塊隱藏）。
- Prefetch：`HomeScreen` 在 hero item 解析後即背景 `PreloadDiyAssetsUseCase`（理想上在 StartedGuide 期間下載完），失敗靜默；點擊時若快取不全走 `DiyPreloadPurpose.QUICK_APPLY` 進度 overlay fallback。
- `HeroQuickApply.apply()`（`NonCancellable`）：trial 記帳**與編輯器同規則**（2026-07-24 改：`freeTrialDays > 0` 給 trial、active trial 保留、購買/premium 永久；事件 `free_trial_started` `entry_point=hero_quick_apply`）→ `DiyWallpaperConfig.save()`（`userImages` 空 → Service 渲染 `sampleAssetId`；stickers / animationTexts 必須從 template 帶入，因為 Service 只從 prefs 讀）→ 若無草稿則 upsert 一列預設 `DiySaveTemplate`（讓收藏頁出現續期/購買 bar）→ `launchLiveWallpaperPreview()`。
- 成功判定：回 App `ON_RESUME` 時用 `WallpaperManager` 確認 service 已生效才記 `hero_apply_success`（原計畫的 `wallpaper_service_started` 事件不存在）。漏斗：`hero_quick_apply → hero_quick_apply_launched → hero_apply_success`。
- 2026-07-24 移除套用後的「換上你的照片？」DIY 橋接 dialog。
- 待確認：後端 settings 是否已上線 `heroItemId`（文件列為待辦）。

## 13. 新增欄位 checklist（Rule 3）

**A. `EditDiyLiveWallpaperScreen` 新增使用者可編輯狀態**（6 步 + 4 步）：
1. `DiySaveTemplate` 加 column
2. `DiySaveSerializer` 加 serialize / deserialize
3. `WallpaperDatabase` 加 MIGRATION（目前 version 10）
4. `doSaveAndApply()` 寫入（Room 與 `DiyWallpaperConfig.save()` 參數）
5. `LaunchedEffect(itemId, fromCollections)` 載入
6. 加 `committed*` var + `hasEdits` 比較式 + DB 載入時更新 baseline + `fromCollections` upsert 後更新 baseline
（Service 端若要渲染，`DiyWallpaperConfig` 也要加 key 與 load 方法。）

**B. `PhotoCardConfig` / `DecorationConfig` / `StickerConfig` / `TextConfig` / `DiyTemplate` 等 config / DTO 增刪改欄位** → 跑 `diy-template-reviewer` agent 追蹤 Dev state → Dev DB snapshot → Domain → JSON → Canvas/Service → Duplicate-to-DB 全 pipeline，並更新 `doc/diy_live_wallpaper_data_flow.md`。歷史教訓：`DebugDuplicateToTemplateBuilderDialog` 曾靜默丟掉 phase2。

## 14. 已知裝置問題與已修正事項

| 現象 | 原因 | 狀態 |
|---|---|---|
| 系統選擇器選「鎖定螢幕」動態桌布沒出現，選「桌面」後兩者都出現 | OEM（三星、小米等）要求引擎先以桌面模式初始化過才可單獨設鎖屏 | **無法從 App 端繞過**；建議順序：先設桌面或桌面+鎖屏，之後才能單獨設鎖屏 |
| 首次設定畫面空白，重開機後才正常 | `apply()` 非同步，Service 在寫入前讀取 | 已修：`commit()` |
| 橫圖放直卡時 Service 比 Preview 放大 | Service 用 fillWidth、Compose 用 Fit | 已修：`fitScaleBitmap` |
| Decoration 比 Preview 寬 | `createScaledBitmap` 拉伸成正方形 | 已修：`fitScaleBitmap` 等比置中 |
| App 更新／重開機後 sample 與 background 消失 | 冷啟動猜 ext 錯 → 快取 miss | 已修：ext-agnostic 掃描，更新後自動復原 |
| 某些 OEM 無 `ACTION_CHANGE_LIVE_WALLPAPER` | ROM 差異 | 三段 fallback（chooser → Toast），事件監控佔比 |
| 靜止時 60fps 空轉耗電 | loop 未停 | 已修：`PAUSING` 停 loop |
| hardware canvas + `recycle()` native crash | texture 仍 pin 住 pixels | 已修：不 recycle，只丟 reference |

## 15. Analytics（編輯器主要事件）

`diy_edit_screen_opened`、`diy_preview_viewed`、`diy_click_edit_background/sticker/add_text`、`diy_photo_added_single/batch`、`diy_click_favorite`、`diy_save_draft`、`diy_exit_save_draft/discard`、`diy_exit_edit_page`、`diy_download_free_ad_clicked/watched/failed`、`free_trial_started`、`diy_purchase_*` 漏斗（見 monetization 頁）、`diy_warning_device_*`。
