---
title: Notifications 與 Workers（FCM、本地提醒、App 更新、網路狀態）
source: raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/service/MessagingService.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/service/TrialExpiryReminderWorker.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/util/Notifications.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/util/TrialExpiryReminderScheduler.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/util/NetworkUtil.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/util/NetworkState.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/components/NotificationOptIn.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/components/AppUpdateBanner.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/components/ForceUpdateDialog.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/MainActivity.kt, raw/PaletteWallAndroid/app/src/main/AndroidManifest.xml
updated: 2026-11-24
confidence: high
---

# Notifications 與 Workers

推播（FCM topic 廣播）、本地到期提醒（WorkManager）、通知權限 opt-in、App 更新提示／強制更新、網路狀態檢查。都是小而獨立的基礎設施，集中在 `service/`、`util/` 與幾個 component。

相關頁：[[projects/PaletteWallAndroid/modules/retention-and-trial]]（提醒的業務規則）、[[projects/PaletteWallAndroid/modules/monetization]]（Remote Config 的廣告 key）、[[projects/PaletteWallAndroid/modules/home-and-browsing]]（banner 擺放位置）、[[projects/PaletteWallAndroid/architecture]]。

## 1. 通知基礎（`util/Notifications.kt`）

| 常數 | 值 | 用途 |
|---|---|---|
| `CHANNEL_ALL_USERS` | `channel_all_users` | FCM 廣播；必須等於 `R.string.default_notification_channel_id`（manifest `default_notification_channel_id` meta-data 也指向它） |
| `CHANNEL_REMINDERS` | `channel_reminders` | 本地提醒（trial 到期），與 FCM 分開讓使用者可各自靜音 |
| `TOPIC_ALL_USERS` | `topic_all_users` | 所有人啟動時訂閱，從 Firebase Console 直接發 retention 廣播，不需後端存 token |

- `createChannels()`：`PaletteWallApplication.onCreate()` 呼叫，冪等，Android O 以下 no-op。
- `syncEnabledUserProperty()`：`MainActivity.onResume()` 把 `NotificationManagerCompat.areNotificationsEnabled()` 寫成 Firebase user property `notifications_enabled`。動機：FCM campaign 232 送達 112 開啟 0——Android 13+ 未授權 `POST_NOTIFICATIONS` 的裝置「收到但不顯示」，`notification_receive` 分不出沒顯示與沒興趣；發 campaign 前先看 `notifications_enabled = true` 人數才是真實可觸達數（Console 需先註冊此 property；BigQuery `user_properties` 不用註冊）。`DEBUG_MODE` 只印 log。
- Manifest：`POST_NOTIFICATIONS`、`c2dm.permission.RECEIVE`、`WAKE_LOCK`；FCM 預設 icon `ic_notification`、色 `notification_accent`。

## 2. FCM（`service/MessagingService.kt`）

- `FirebaseMessagingService`，manifest 註冊 `MESSAGING_EVENT`。
- `onNewToken`：token 輪替時重新 `subscribeToTopic(TOPIC_ALL_USERS)`（targeting 完全 topic-based，App 不上傳 token；`MainActivity.fetchFirebaseToken()` 每次啟動也訂閱一次，冪等）。
- `onMessageReceived`：title / body 取 `notification` 區塊，否則 `data["title"]` / `data["body"]`，否則 App 名稱 → `sendNotification()` 以 `CHANNEL_ALL_USERS` 發，點擊開 `MainActivity`（`FLAG_ACTIVITY_CLEAR_TOP`），固定 notification id 0。
- 背景收到的「notification message」由系統直接顯示（走 manifest 預設 channel / icon），不經過此 service。
- 限制：**沒有 deep link**，通知只能開首頁（retention 計畫 Tier 1c 待做）；FCM 週播「本週限免」（Tier 2a）也尚未做。

## 3. 通知權限 opt-in（`ui/components/NotificationOptIn.kt`）

- `rememberNotificationOptIn()` 回傳 `NotificationOptInState`；在正向時刻（DIY 套用桌布後、靜態桌布設定後回 App）呼叫 `maybeRequest()`。
- 條件：Android 13+、尚未授權、**從未問過**（SharedPrefs `notification_optin.asked` 一次性 flag）。先顯示軟性 pre-prompt AlertDialog（不可外點／back 關閉），Yes → 系統權限對話框（`diy_notification_click_yes`），No → `diy_notification_click_no`。
- 回傳 true 表示本輪已顯示，呼叫端跳過同一輪的 In-App Review。
- 收藏頁的到期提醒 toggle 另有自己的權限流程（API 33+ `RequestPermission`；已永久拒絕時系統不再跳 → 導 `ACTION_APP_NOTIFICATION_SETTINGS` 或 toast）。

## 4. WorkManager：Trial 到期提醒

### 4.1 排程（`util/TrialExpiryReminderScheduler.kt`）

```
REMINDER_LEAD_MS = 3 天；MIN_DELAY_MS = 1 小時；MIN_REMAINING_MS = 2 小時
reschedule():
  cancelAllWorkByTag("trial_expiry_reminder")
  if (!TrialReminderPrefs.isEnabled) return
  for record in diy_unlock_record where expiresAt > now + 2h:
      delay = max(expiresAt − 3d − now, 1h)
      enqueueUniqueWork("trial_reminder_{itemId}", REPLACE, OneTimeWorkRequest<TrialExpiryReminderWorker>(delay, input itemId, tag))
```

- 冪等：每次都 cancel 後從 DB 全量重排，自然處理續期（delay 變長）、刪除（無 row 無 work）、toggle 關閉（全部取消）。
- 呼叫點：收藏頁 toggle 切換、每次 `DiyUnlockRecord` 寫入／刪除（編輯器看廣告開 trial、Hero 套用、收藏頁續期、購買轉永久、刪草稿）、`MainActivity.onCreate` 安全網（WorkManager 重開機自帶恢復，但 force-stop / OEM 電池殺進程會清掉，下次啟動自癒）。
- `TrialReminderPrefs`（SharedPrefs `trial_reminder.enabled`，預設 OFF，`commit()`）。
- 依賴 `work-runtime-ktx 2.9.1`，不需 hilt-work（Worker 直接 `WallpaperDatabase.getDatabase()`，本專案 DAO 不走 Hilt）。

### 4.2 Worker（`service/TrialExpiryReminderWorker.kt`）

`CoroutineWorker.doWork()` 觸發時**從 DB 重驗證**，任一條件不符即 `Result.success()`（永不 retry，過時的 work 是無害 no-op）：

1. pref 仍開啟
2. record 存在、`expiresAt > 0` 且未過期
3. 剩餘 ≤ 3 天 + 12 小時 slack（吸收 Doze 延後）
4. 系統通知仍啟用

然後以 `CHANNEL_REMINDERS` 發通知（標題／內文是 generic 字串，因 `DiyUnlockRecord` 沒有名稱欄位），`PendingIntent` 的 requestCode 與 notification id 都用 `itemId.hashCode()`（**不可共用 0**，多個提醒會互相覆蓋），extras `open_tab=Favorite` + `notification_source=trial_reminder`；記 `trial_reminder_shown`（`item_id`、`remaining_days`）。

### 4.3 點擊導航

`MainActivity.onCreate` 只在 `savedInstanceState == null` 時讀 `EXTRA_OPEN_TAB` / `EXTRA_NOTIFICATION_SOURCE` 並 `removeExtra`（語言切換 `recreate()` 會重跑 onCreate，不能重複觸發），記 `notification_open{source}`，再經 `NavigationPage(initialTab)` navigate 到 `PaletteWallPage?tab=Favorite`（`popUpTo inclusive + launchSingleTop`）。

測試加速方法見 `doc/tester_note.md` 第 4 節（改 `REMINDER_LEAD_MS` 與 `MIN_DELAY_MS`）；排程狀態可用 Android Studio Background Task Inspector 看 `trial_reminder_<itemId>`。

## 5. App 更新：banner 與強制更新

兩個機制都由後端 `GET items/settings/init` → `AppSettings` 驅動（Gson 缺欄位 → 0 / null → 功能自然關閉，fail-open），版本資訊由 `MainActivity.initializeVersionName()` 注入 `HomeViewModel`（`setVersionName` / `setInstalledVersionCode`）。

| 機制 | 欄位 | UI | 觸發 |
|---|---|---|---|
| 更新提示 banner | `latestVersionCode` / `latestVersionName`（nullable） | `AppUpdateBanner`：取代 Live tab 的 `DiyTipsCarousel` 位置（同兩行高，列表不跳動） | `HomeViewModel.updateBannerVersionName`：installed < latest 且 installed 不是 0/1（本機測試 build；Bitrise 才注入真實 versionCode） |
| 強制更新 | `minVersionCode`（0 = 停用） | `ForceUpdateDialog`：不可關閉（back / 外點皆無效），唯一按鈕「立即更新」；掛在 `MainActivity.setContent` 最外層、`NetworkErrorDialog` 之後（疊最上） | `HomeViewModel.forceUpdateRequired = minVersionCode > 0 && installed in 1 until minVersionCode`；更新完成 process 重啟自動消失 |

- 兩者都接 `MainActivity.requestUserTriggeredUpdate()`：Play 回報有更新 → FLEXIBLE 優先、否則 IMMEDIATE；無更新 / sideload / 查詢失敗 → 開 Play Store 頁（`market://` → https fallback）。
- 啟動時另有自動 `checkForAppUpdates()`（FLEXIBLE 優先）；`InstallStateUpdatedListener`：`DOWNLOADING` 一次性 toast「更新下載中」、`DOWNLOADED` toast「更新完成，即將重新啟動」後 `completeUpdate()` **立即安裝重啟**（toast 只是提示，非確認）。`onResume` 檢查已下載未安裝或進行中的 IMMEDIATE 更新。
- 營運約束：`minVersionCode` 必須 ≤ Play 全量發布版本，staged rollout 期間不可調高，否則所有人被鎖。這是 API token 驗證 Phase 3（切 hard mode）前壓低舊版流量的工具。
- settings 抓取節流 60 秒，`onResume` 的 `refreshAppSettingsOnResume()` 與 Live tab 的 refresh 共用戳記；測試時直接殺 App 重開最快。

這與 Firebase Remote Config 是**兩套東西**：Remote Config（`PaletteRemoteConfig`）只管廣告模式與 ad unit id；版本控制走自家 settings API。

## 6. 網路狀態

| 元件 | 說明 |
|---|---|
| `util/NetworkUtil.isNetworkAvailable()` | 一次性同步檢查：`activeNetwork` 具 `NET_CAPABILITY_INTERNET` **且 `NET_CAPABILITY_VALIDATED`**（系統實測可上網；排除飛航模式、無網 WiFi、飯店 captive portal）。零成本、不發請求。Manifest 有 `ACCESS_NETWORK_STATE` |
| `util/NetworkState.rememberIsNetworkAvailable()` | Composable 版：`registerDefaultNetworkCallback`，`onAvailable / onLost / onUnavailable / onCapabilitiesChanged` 都重讀 active network（VALIDATED 在 available 之後才翻真，所以 capabilities 回呼不可少）；用於首頁回饋列這類「只在線上才顯示」的 UI |
| `ui/components/NetworkErrorDialog.kt` | 單鈕 AlertDialog「網路錯誤，請檢查連線」 |

檢查點：`MainActivity.onResume`（全域 dialog）、所有 Rewarded Ad request 之前（`DiyLiveModal`、收藏頁續期、農場領花——因 `RewardedAdState` 失敗仍給獎，否則離線可免費解鎖）、pull-to-refresh（`LiveWallpaperPage` / `MainPageContent` / `SeeMoreScreen`，無網路不打 API）。未採用：HTTP `generate_204` 探測（要發請求）。

## 7. 其他背景元件

- `MainActivity` 的 `ACTION_DOWNLOAD_COMPLETE` BroadcastReceiver（`RECEIVER_EXPORTED`）：靜態桌布 DownloadManager 完成 → `updateDownloadBtnStatus(2)`。
- `DebugAnalyticsToggle`（`util/`）：設定頁點版本 10 次切換 Firebase Analytics 收集，持久化於 SharedPrefs，App 啟動 `applyPersistedState()`。
- `DiyLiveWallpaperService` 也是 manifest 註冊的 service（`BIND_WALLPAPER`、`@xml/wallpaper_diy`），見 [[projects/PaletteWallAndroid/modules/diy-live-wallpaper]]。

## 8. 待確認 / 未做

- 後端 settings 是否已送 `latestVersionCode` / `minVersionCode` / `serverTimeUtcMs` / `heroItemId`（App 端對缺欄位皆安全）。
- Deep link（`palettewall://` scheme 或 App Links）未實作；FCM 與本地通知目前只能落在首頁 tab。
- 本地通知頻率上限（計畫：每週 ≤ 2 則）目前只有單一種提醒，尚無全域節流。
- 桌面 Widget、FCM 定期限免廣播均為規劃項目，見 [[projects/PaletteWallAndroid/plans]]。
