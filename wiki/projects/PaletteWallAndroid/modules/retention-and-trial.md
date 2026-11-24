---
title: Retention 與免費 Trial（花朵系統、每週限免、試用到期、評分與回饋）
source: raw/PaletteWallAndroid/doc/free_system_redesign_plan.md, raw/PaletteWallAndroid/doc/flower_retention_and_trial_plan.md, raw/PaletteWallAndroid/doc/tester_note.md, raw/PaletteWallAndroid/doc/changelog.md, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/util/TrustedTime.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/util/FeatureFlags.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/screens/farm/, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/components/InAppReview.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/components/FeedbackPromptRow.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/util/FeedbackPrefs.kt
updated: 2026-11-24
confidence: high
---

# Retention 與免費 Trial

這頁整理「讓使用者回來」的機制：**免費系統（每週限免 + 限時 trial + 免費續期）**是目前上線的主線；**花朵收集系統**（農場簽到、花朵兌換）在 2026-07-14 被 feature flag 封存但程式碼保留；另外有 In-App Review、首頁回饋列、到期提醒通知。

相關頁：[[projects/PaletteWallAndroid/plans]]（兩份計畫書的脈絡）、[[projects/PaletteWallAndroid/modules/monetization]]（廣告與 `DiyUnlockRecord`）、[[projects/PaletteWallAndroid/modules/diy-live-wallpaper]]（Service 到期 overlay）、[[projects/PaletteWallAndroid/modules/notifications-and-workers]]（到期提醒 Worker）、[[projects/PaletteWallAndroid/data-model]]。

## 1. 時間線（兩份計畫如何疊加）

| 日期 | 計畫 | 狀態 |
|---|---|---|
| 2026-07-08 ~ 07-10 | `doc/flower_retention_and_trial_plan.md`：花朵收集（農場簽到 / 每日開花 / 更新獎勵）+ 花朵兌換 30 天 trial + Service 到期 overlay + Welcome 頁 | client P1–P6 **已實作** |
| 2026-07-14 | `doc/free_system_redesign_plan.md`：每週限免、免費＝trial、免費續期、Trusted Time、**花朵系統封存** | client **已實作**（`assembleProdDebug` 通過） |
| 2026-07-19 | 續期改為看廣告；購買後清 trial；到期前 3 天通知 toggle | 已實作 |
| 2026-07-23 | 續期增量改 `freeTrialDays`；`DiyLiveModal` 文案動態化；StartedGuidePage | 已實作 |
| 後端 | `live_items` 的 `freeOnDaysOfWeek` / `maxTrialDays` / `freeTrialDays` / `flowerCost`；settings 的 `serverTimeUtcMs` / `heroItemId` | **待確認**（`doc/free_system_backend_todo.md` 列為待辦；App 端對缺欄位全部 fail-safe） |

## 2. 免費系統（目前主線，已實作）

### 2.1 規則

| 概念 | 欄位（`DiyWallpaperItem`） | 規則 |
|---|---|---|
| 永久免費 | `freeDownload: Boolean` | 既有欄位 |
| 每週限免 | `freeOnDaysOfWeek: List<Int>`（ISO 1=週一…7=週日，可多日，空＝無） | `isFreeNow(todayDow) = freeDownload \|\| (todayDow != 0 && todayDow in freeOnDaysOfWeek)` |
| 免費＝限時 | `freeTrialDays: Int`（0 = 免費即永久，legacy） | 看完廣告後 `expiresAt = now + freeTrialDays × 1 天` |
| 剩餘時間上限 | `maxTrialDays: Int`（default 30；DTO 缺欄位是 0 → mapping 改 30） | 收藏頁倒數 bar 分母；續期上限 |
| 免費續期 | client 計算 | `newExpiresAt = min(max(expiresAt, now) + freeTrialDays(≤0 則 30), now + maxTrialDays)`；2026-07-19 起**要看一支 Rewarded Ad**，隨時可續 |

Gson 繞過 constructor default：`freeOnDaysOfWeek` 宣告 `List<Int>? = null` 在 mapping 補 `?: emptyList()`；`maxTrialDays` 缺欄位是 0 → 補 30。舊版 App 不認得新欄位 → 限免 item 走購買 modal，不 crash。

### 2.2 Trusted Time（`util/TrustedTime.kt`）

- **只用於「今天星期幾」判定**（限免 FREE tag 與 gating）。**trial 到期 / 倒數 / 續期 / Service 全部維持 `System.currentTimeMillis()`**（2026-07-14 PO 決策：防改時鐘是為了限免日正確，不是防使用者延長 trial；回撥時鐘延長 trial 屬接受行為）。
- `sync(context, serverTimeUtcMs)`：`getAppSettings()` 成功後記 `(serverTimeUtcMs, SystemClock.elapsedRealtime())` 錨點到 SharedPrefs `trusted_time`；`serverTimeUtcMs <= 0`（後端未上線）直接忽略。
- `todayDayOfWeek()`：`now = anchor_server + (elapsedRealtime - anchor_elapsed)`（elapsedRealtime 單調、改牆鐘動不了）→ 裝置時區的 ISO 星期。**無錨點或重開機後（elapsedRealtime < 錨點）回 0 → fail-closed**，限免日整個不生效，**沒有裝置時鐘 fallback**。
- `nextRotationMs()`：下一個本地午夜，首頁 Free Today 右下角「下一次更新時間」用。
- 接線：`HomeViewModel.getAppSettings()` 與 `refreshAppSettingsOnResume()`（`MainActivity.onResume`，60 秒節流）→ sync → `refreshTodayDayOfWeek()`；`LiveWallpaperPage` 以 `LocalTodayDayOfWeek` CompositionLocal 供給卡片，`ON_RESUME` 重算處理跨午夜。
- 副作用（接受）：離線 / API 失敗 / 重開機未連網看不到限免 tag（離線本來也看不了廣告）；改時區最多偏移 ±1 天。
- 未採用的替代：Google Play `TrustedTimeClient`（多一個 GMS 依賴）。

### 2.3 使用者流程

```
首頁卡片 isFreeNow → 藍色 FREE tag；Free Today 群組置頂（永久免費 + 今日限免）
→ 編輯器 Save → DiyLiveModal「觀看廣告（免費用 N 天）」+「到期前可一直免費續期」
→ 看完廣告 → upsert DiyUnlockRecord(itemId, now, now + N 天) → reschedule 提醒 → doSaveAndApply(expiresAt)
→ SharedPrefs expires_at（commit）→ Service 到期判定
→ 收藏頁 SAVED 分頁：TrialCountdownBar（remaining / maxTrialDays，到分鐘；<50% 時續期鈕白框呼吸閃爍）
   + 滿寬「免費續期」（看廣告）+ 「{price} 永久取得」（Play 即時價）
→ 到期：桌布畫 scrim +「桌布已到期」+「開啟 PaletteX → 我的收藏 / 點『免費續期』繼續使用」
→ 回 App 續期 → DiyWallpaperConfig.updateExpiresAt() 同步快照 + bump save_version → Service 下次可見 reload、overlay 消失
```

其他已實作細節：
- trial 生效中再 Save 同 item **不重設**（避免重看廣告重置時間）。
- 購買完成（`BillingViewModel.handlePurchase`）→ unlock record 改 `expiresAt = 0`、取消提醒；收藏頁 `trialRecord` 判定加 `itemId !in purchasedWallpapers` 讓 UI 先行隱藏倒數。
- 刪除草稿（收藏頁 / 編輯器）→ `deleteByItemId` 撤銷 trial，下次要重看廣告；已套用桌布不受影響。
- 收藏頁 DIY universe = 最愛 ∪ 已購買 ∪ 已儲存 ∪ 有 unlock record；分頁順序 已儲存 / 我的最愛 / 已購買（預設已儲存）。
- Hero 一鍵套用走同一套 trial 規則（2026-07-24）。
- 靜態桌布不做 trial（走系統 intent、原圖已在 Downloads，強制到期做不到）。

### 2.4 Analytics

`free_trial_started`（`trial_days`、`source = free_download / free_weekday`、`entry_point`）、`free_trial_active_SaveAndApply`、`collection_renew_clicked`（`remaining_days`）、`collection_renew_ad_fallback`、`collection_dialog_renew_ok_click`（`extended_days`、`remaining_days_after`；原名 `free_trial_renewed`）、`collection_delete_saved_clicked` / `collection_dialog_delete_ok_click`、`collection_purchase_2_CHECKOUT_STARTED`。BigQuery 既有查詢需配合改名。

## 3. 花朵系統（已實作、已封存）

`util/FeatureFlags.kt`：

```kotlin
object FeatureFlags { const val FLOWER_SYSTEM_ENABLED = false }
```

設為 `true` 可整套復活。封存方式是用 `if (FeatureFlags.FLOWER_SYSTEM_ENABLED)` 包住入口，**不註解、不刪檔、Room 表不做破壞性 migration**（`flower_basket` 餘額原樣留存）。

### 3.1 被隱藏的入口

`HomeTopBar` 的 `FlowerCounterBadge`（補回 48dp 佔位）、`LiveWallpaperPage` 的 `GetFreeFlowersButton` 與 `AppUpdateRewardButton`、board 的 `NAVIGATION_FLOWER_FARM`、`DrawerContent` 農場列、`DiyTipsCarousel` 花朵 tips、`DiyLiveWallpaperCard` 的 `FlowerCostTag`、編輯器 `FlowerTrialModal` 分支與 `redeemWithFlowers()`、`DiyLiveWallpaperSaveButton` 的花朵 badge、收藏頁扣花續期、`DeveloperSettingsSection` 花朵餘額調整列。`Screen.Farm` 路由仍註冊但無入口可達。

### 3.2 保留的實作（復活時可直接用）

| 元件 | 說明 |
|---|---|
| `FlowerBasket`（Room 單列 id=1） | `balance`（0..24）、`streakDay`、`lastClaimEpochDay`、`welcomeSeen`、`lastBloomAt`、`rewardedVersionCode`。獨立 entity 而非塞進 `UserSettings`：settings 是整列 REPLACE，與高頻領花/扣花並發會 lost update |
| `FlowerBasketDao` | 全部用 **SQL 原子條件 UPDATE** 防並發與時鐘回撥：`claim()`（`lastClaimEpochDay < :today`）、`bloomClaim(now)`（24h 冷卻）、`grantVersionReward()`（版本獎勵一次）、`spend(cost)`（`balance >= cost`）、`devAdjustBalance()`；`ensureRow()` 的 INSERT 必須列出所有 NOT NULL 欄位，否則 fresh install 被 `OR IGNORE` 吞掉、basket 永遠建不出來 |
| `FarmScreen` / `FarmViewModel` | 三區塊：花籃 8×3 格子、每日開花（`DailyBloomButton`，24h 冷卻、⏱ 倒數）、連續簽到 **7 天循環**（Day1=1 / Day2..6=3 / Day7=7 朵；漏一天重置 Day1）。每次領取先 `NetworkUtil` 檢查 → `RewardedAdState.load` → `onEarned` 才入帳；`today = LocalDate.now().toEpochDay()` 為 state，`ON_RESUME` 重算 |
| `FlowerTrialModal` + `FlowerRedeemResultDialog` | 兌換 N 朵 → 30 天 / 購買永久；不足 → 「前往收集花朵」；成功 → 「前往收藏頁 / 套用桌布」。`FlowerRedeemResultDialog` 現在也被免費續期 dialog 重用（`flowerCost = null` 隱藏花朵列，`isLoading` 鎖按鈕） |
| `FlowerIcon` / `FlowerCostTag` / `FlowerGradientColors` | 統一花朵視覺（`R.drawable.flower`，不用 emoji）；橘→粉→紫漸層也被 Free Today tag、續期 pill、倒數 bar 沿用 |
| `GetFreeFlowersButton`、`AppUpdateRewardButton` | 浮動 CTA、安裝/更新一次性 +1 朵 |
| Analytics | 全部 `flower_` 前綴（`flower_tapped_streak_day_N`、`flower_claim_no_network`、`flower_claim_ad_failed`、`flower_farm_claim_completed`、`flower_trial_*` …） |

花朵計畫的經濟設計（`flowerCost = 5~6`、cap 24 允許溢出作廢、no-fill 仍發獎）與 v2 選配（後端錢包、防改時鐘對帳、到期推播）見 [[projects/PaletteWallAndroid/plans]]。

## 4. 到期提醒通知（已實作，2026-07-19）

- 收藏頁 SAVED 分頁 `TrialReminderToggleRow`（預設 OFF，存 `TrialReminderPrefs`）；開啟需通知權限（Android 13+ 走 `RequestPermission`，拒絕則 toast 維持 OFF；app 層被關則導系統設定）。
- `TrialExpiryReminderScheduler.reschedule()`：cancel by tag 後從 `diy_unlock_record` 全量重排 WorkManager one-time work（每 item unique、REPLACE、`delay = max(expiresAt − 3 天 − now, 1 小時)`，剩 <2 小時跳過）。呼叫點：toggle、每次 unlock record 寫入 / 刪除、`MainActivity.onCreate` 安全網。
- `TrialExpiryReminderWorker` 觸發時從 DB 重驗證再發；點通知落在收藏頁。細節見 [[projects/PaletteWallAndroid/modules/notifications-and-workers]]。

## 5. In-App Review 與回饋

| 機制 | 檔案 | 觸發條件 |
|---|---|---|
| Google Play In-App Review | `ui/components/InAppReview.kt` | `requestIfEligible(activity)`：本地 14 天冷卻（SharedPrefs `in_app_review`），Google 自己再決定顯示與否；DEBUG 用 `FakeReviewManager`。呼叫點：DIY 編輯器套用桌布後回 App、`FullscreenScreen` 設定靜態桌布後 `ON_RESUME`。若當輪已顯示通知 opt-in 預提示則跳過 |
| 首頁回饋列 | `ui/components/FeedbackPromptRow.kt`（`LazyListScope.feedbackPromptRow`） | `LiveWallpaperPage` 底部；只在 `!FeedbackPrefs.hasInteractedFeedbackPrompt()` 且**在線**時顯示。「Good」→ `feedback_page?startOnRate=true`（導 Play 評分）；「可以更好」→ `feedback_page?startOnImprove=true`。點任一鈕即 `markFeedbackPromptInteracted()` 永久隱藏（事件 `home_feedback_good_clicked` / `home_feedback_could_be_better_clicked`） |
| 意見反饋 / 錯誤回報 | `ui/screens/feedback/FeedbackScreen.kt`、`BugReportScreen.kt`、`FeedbackViewModel.kt`、`util/FeedbackPrefs.kt` | `POST /api/feedback`（截圖走 `POST /api/feedback/upload-url` presigned）。防濫發：建議每 7 天 1 次、bug 回報 7 天滾動視窗最多 3 次，**換 versionCode 即重置**；每次帶隨機 per-install `deviceId`（非使用者身分）。Settings 頁也有入口（`feedback_advice_clicked` / `feedback_bug_report_clicked`） |

## 6. Onboarding（與 retention 相關）

- `StartedGuideScreen.kt`（2026-07-23）：首次啟動 overlay（非 navigation destination，蓋在首頁上讓首頁在底下先載入）：Welcome 段（品牌列 + ExoPlayer mp4 hero + 文案）→ 3 頁功能輪播（每天更新免費桌布 / 無限延長試用 / 多功能編輯）。`welcome_seen` 以 SharedPrefs 鏡像 + Room `welcomeSeen` 雙寫（鏡像讓第一個 frame 就能同步決定，避免閃 Home 0.2 秒）。事件 `started_guide_page_shown/closed`（`click_close_button_on_page` 0=welcome、1..3=輪播頁）。
- `WelcomeScreen.kt` 的 `WelcomeOverlay` 已 `@Deprecated`，共用 `WelcomeHeroVideo`。
- 待確認：輪播三頁插圖仍為 placeholder（changelog 列待辦）。

## 7. 測試技巧（`doc/tester_note.md`）

- Trial 到期：把三個寫入點的 `86_400_000L` 暫改 `60_000L`（1 天 = 1 分鐘），測完還原；收藏頁倒數會不準但 overlay 時機準。
- 簽到：改裝置日期 +1 天（只能往前；測完清 App 資料）；或 `FarmViewModel` 三處 `toEpochDay()` 改分鐘（還原後必須清資料，否則永久卡死）。
- 到期提醒：`REMINDER_LEAD_MS` 改 40 天、`MIN_DELAY_MS` 改 10 秒，開 toggle 約 10 秒後通知。
- 強制更新：後端 `minVersionCode` 改大，或 `forceUpdateRequired` 暫改恆 true。

## 8. 待確認 / 規劃中

- 後端四個 item 欄位與 `serverTimeUtcMs` 是否已上線（client 已 fail-safe）。
- `doc/retention_maximization_plan_2026-07-15.md` 的 Tier 1–2 項目：本地排程通知（**已做**到期提醒）、deep link（未做，通知只能開首頁指定 tab）、桌面 Widget（未做）、FCM 週播「本週限免」（未做）、分享浮水印（未做）、輕量簽到（未做，且明言不復活農場）。
- 花朵系統若兩個 release 後確定不復活，計畫另開清除任務整批移除。
