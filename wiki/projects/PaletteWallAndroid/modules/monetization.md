---
title: Monetization（Google Play Billing、AdMob 廣告、解鎖紀錄）
source: raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/screens/home/BillingViewModel.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/screens/home/AdManager.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/components/RewardedAdState.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/ui/components/*Modal.kt, raw/PaletteWallAndroid/app/src/main/java/com/palettex/palettewall/util/AdRevenueLogger.kt, raw/PaletteWallAndroid/data/PaletteRemoteConfig.kt, raw/PaletteWallAndroid/scripts/README.md, raw/PaletteWallAndroid/doc/changelog.md
updated: 2026-11-24
confidence: high
---

# Monetization（付費與廣告）

三條收入路徑：**訂閱**（週 / 月 premium，去廣告 + 無限下載）、**一次性購買**（每個 DIY template 或付費靜態桌布一個 productId = `itemId`）、**AdMob 廣告**（底部 banner + Rewarded Ad 解鎖免費內容）。解鎖狀態的本地紀錄是 Room `diy_unlock_record`。

相關頁：[[projects/PaletteWallAndroid/modules/diy-live-wallpaper]]（Save gating）、[[projects/PaletteWallAndroid/modules/retention-and-trial]]（免費 trial 與續期）、[[projects/PaletteWallAndroid/modules/home-and-browsing]]（靜態桌布下載流程）、[[projects/PaletteWallAndroid/data-model]]、[[projects/PaletteWallAndroid/architecture]]。

## 1. 元件總覽

| 元件 | 檔案 | 職責 |
|---|---|---|
| `BillingViewModel` | `ui/screens/home/BillingViewModel.kt` | Google Play Billing Library 8.0.0 client；`isPremium`、`purchasedProductIds`、`isAlreadyPurchase`、價格查詢、購買流程、acknowledge、漏斗事件 |
| `SubscriptionModal` | `ui/components/SubscriptionModal.kt` | 週 / 月訂閱 bottom sheet（價格由 `getSubscriptionPrices()` 即時填入，含政策文字） |
| `OneTimePurchaseModal` | `ui/components/OneTimePurchaseModal.kt` | 單品購買 sheet；開啟時查價（5 秒逾時）；CTA 顯示「Unlock for {price}」 |
| `AvailableDownloadPremiumModal` | `ui/components/AvailableDownloadPremiumModal.kt` | Premium 使用者下載靜態桌布的確認 sheet |
| `NormalModal` | `ui/components/NormalModal.kt` | 靜態桌布：看廣告免費下載 / 付費取得 |
| `DiyLiveModal` | `ui/components/DiyLiveModal.kt` | DIY 免費 item：看 Rewarded Ad 套用（`freeTrialDays > 0` 時文案改成「免費用 N 天」+ 續期提示），下方可選購買按鈕 |
| `FlowerTrialModal` | `ui/components/FlowerTrialModal.kt` | 花朵兌換 / 購買（feature flag 關閉，保留） |
| `RewardedAdState` | `ui/components/RewardedAdState.kt` | 唯一的 Rewarded Ad 邏輯 |
| `AdManager` | `ui/screens/home/AdManager.kt` | 底部 banner `AdView` singleton 與 2 分鐘刷新 |
| `AppUpdateRewardButton` | `ui/components/AppUpdateRewardButton.kt` | 安裝／更新獎勵（送花，無廣告；隨花朵 flag 隱藏） |
| `AdRevenueLogger` | `util/AdRevenueLogger.kt` | 曝光層級收益記到 Firebase `ad_revenue_paid` |
| `PaletteRemoteConfig` | `data/PaletteRemoteConfig.kt` | Firebase Remote Config：廣告開關與 ad unit id |
| `DiyUnlockRecord` / `DiyUnlockRecordDao` | `data/local/entity/`, `data/local/dao/` | 解鎖紀錄（`expiresAt = 0` 永久） |
| `scripts/set_onetime_price.py` | `scripts/` | 批次改 Google Play 一次性商品定價 |

## 2. BillingViewModel

- `@HiltViewModel`，`MainActivity` 持有單一實例，透過 `NavigationPage` 傳給各畫面。
- 啟動時 `setupBillingClient()` → `onBillingSetupFinished` → `queryPurchases()`：同時查 `SUBS` 與 `INAPP`，彙整成 `_purchasedProductIds`；`isPremium` 只看訂閱商品（`subscriptionProductIds` 集合內），單品購買不算 premium。
- `setCurrentProductId(itemId)`：畫面進入某個 item 時呼叫，更新 `isAlreadyPurchase`。**不能**在這裡清 `processingProductId`（Play 付款頁開著時被重組呼叫會漏記 CANCELED / FAILED）。
- `refreshPurchases()`：畫面進入／App resume 時呼叫以捕捉 `PENDING → PURCHASED`（silent 模式不跳 toast）。
- `handlePurchase()`：
  - `PURCHASED` 未 acknowledge → `acknowledgeWithRetry()`（指數退避）。
  - 非訂閱商品若有 `expiresAt > 0` 的 `DiyUnlockRecord` → upsert 為 `expiresAt = 0`（永久）+ `DiyWallpaperConfig.updateExpiresAt(_, _, 0)` 同步套用中桌布 + `TrialExpiryReminderScheduler.reschedule()` 取消提醒。冪等，restore 時 `expiresAt == 0` 直接跳過。
  - `PENDING` → 記 `diy_purchase_3b_PENDING`。
- 成功事件 `diy_purchase_3_COMPLETED` 只在 `purchasesUpdatedListener`（使用者剛完成的即時購買）記，不在 `handlePurchase`（每次啟動 restore 都會跑）。
- 價格：
  - `getOneTimePurchasePrice(productId, callback)`：`queryProductDetailsAsync` → `oneTimePurchaseOfferDetails.formattedPrice`，去尾零（`99.00 → 99`）並補幣別；結果快取在 `_productPrices`（`getCachedPrice()` 供收藏頁即時顯示）。
  - `getSubscriptionPrices(callback)` 回週 / 月價格 map。
  - **原則：售價永不 hardcode**，`DiyWallpaperItem` 沒有 `price` 欄位（CLAUDE.md Rule 8）。
- 購買：`launchBillingFlow(activity, subscriptionType)`（訂閱）、`launchBillingFlowWithOneTimePurchase(activity, productId)`（單品）。
- 2026-07-23 升級 Billing 8.0.0（Play 政策）：callback 改用 `QueryProductDetailsResult.productDetailsList`；連動 Kotlin 2.0.21 / Hilt 2.51.1。暫不升 9.x（需 Kotlin 2.2）。

### 購買漏斗事件（GA4）

| 事件 | 時機 |
|---|---|
| `diy_purchase_1_LOCK_TAPPED_SaveAndApply` | 編輯器 Save 碰到付費 gating |
| `diy_purchase_modal_opened` / `diy_purchase_modal_dismissed` | `OneTimePurchaseModal` |
| `diy_purchase_price_load_failed` | ViewModel 端三種失敗（client 未 ready = -1、非 OK = responseCode、商品/offer 缺）；modal 端只記「5 秒完全沒 callback」（-2） |
| `diy_purchase_2_CHECKOUT_STARTED` | 點購買 CTA（`OneTimePurchaseModal` / `DiyLiveModal` / `FlowerTrialModal`）；收藏頁用 `collection_purchase_2_CHECKOUT_STARTED` |
| `diy_purchase_3_LAUNCH_FAILED` | `launchBillingFlow` 沒成功彈出 Play 付款頁（2026-07-28 補，先前漏斗看起來像用戶蒸發） |
| `diy_purchase_3_COMPLETED` / `_CANCELED` / `_FAILED` / `_3b_PENDING` | listener 結果；帶 `value` + `currency`（`putCachedPrice`） |
| `diy_purchase_purchased_SaveAndApply` | 已購買者直接套用 |
| `diy_purchase_apply_now_tapped` / `_apply_later_tapped` | 購買成功 dialog |

注意：GA4 裡 2026-06-28 的 TWD 99 成交是開發者測試單，分析要排除。

## 3. 廣告

### 3.1 Remote Config 開關（`PaletteRemoteConfig`）

| Key | 用途 |
|---|---|
| `mode_DownloadReward` | 0 = 不顯示 Rewarded Ad；1 = debug（測試 ad unit）；其他 = 正式 |
| `AdUnitID_DownloadReward` | Rewarded ad unit id |
| `mode_BottomBanner` / `AdUnitID_BottomBanner` | 底部 banner 同上 |

`MainActivity.initializeRemoteConfig()` 設定 fetch 間隔（DEBUG 0 秒、正式 3600 秒）、載入 `R.xml.remote_config_defaults`，`fetchAndActivate` 成功後 `PaletteRemoteConfig.updateLocalValues()` 並 `setIsRemoteConfigInitialized(true)`。`MobileAds.initialize()` 只在非 premium 時執行。`BuildConfig.DEBUG_MODE` 或 remote debug mode 一律用 Google 測試 ad unit。

### 3.2 Rewarded Ad（`RewardedAdState`）

```kotlin
fun load(onBeforeShow = {}, onAdLoaded = {}, onAdFailed = {}, onEarned: () -> Unit)
var isLoading: Boolean   // mutableStateOf，按鈕 disabled + spinner 直接觀察
```

- `if (isLoading) return` 防重複觸發；`onBeforeShow` 在廣告即將出現（或失敗）時呼叫，讓 modal 先關閉。
- **優雅降級**：載入失敗或播放失敗**仍呼叫 `onEarned`**（no-fill 不打斷使用者），並先呼叫 `onAdFailed` 讓呼叫端記錄降級比例（`diy_download_free_ad_failed`、`flower_claim_ad_failed`、`collection_renew_ad_fallback`）。`onAdLoaded` 只在真正載入成功時觸發。
- 因為降級會給獎，**所有呼叫點在 request 前先 `NetworkUtil.isNetworkAvailable()`**（要求 `NET_CAPABILITY_VALIDATED`），無網路彈 `NetworkErrorDialog`，否則飛航模式可免費解鎖（2026-07-08 修補）。
- 載入成功即 `setOnPaidEventListener` → `AdRevenueLogger`。
- 呼叫點：`DiyLiveModal`（DIY 免費套用）、`NormalModal`（靜態桌布免費下載）、`LikeCollectionScreen` 續期 dialog（2026-07-19 起續期要看廣告）、`FarmScreen`（花朵，flag 關閉）。

### 3.3 Banner（`AdManager`）

- `getOrCreateAd()` 建立單一 `AdView`（BANNER size），`loadAdIfNeeded()` 在首次 / 強制 / 超過 `refreshInterval`（成功 2 分鐘、失敗 1 分鐘）時 `loadAd`，結果寫回 `HomeViewModel.setBottomAdsLoaded()`。
- `BottomBarBox` 在 `!isPremium && shouldShowBannerAds()` 時以 `AndroidView` 顯示；`MainActivity.onResume` 在 remote config 就緒後呼叫 `loadAdIfNeeded`；`onDestroy` → `cleanup()`。
- 2026-07-15 曾暫時隱藏、07-19 還原。

### 3.4 收益記錄（`AdRevenueLogger`）

AdMob↔Firebase 連結不會把收益金額匯出 BigQuery，所以自己從 `OnPaidEventListener` 送 `ad_revenue_paid`：`value`（`valueMicros / 1e6`）、`currency`、`precision`（0 UNKNOWN / 1 ESTIMATED / 2 PUBLISHER_PROVIDED / 3 PRECISE）、`ad_format`（`rewarded` / `banner`）、`ad_unit_id`、`ad_source`（mediation adapter）。`DEBUG_MODE` 只印 log 不上報（測試廣告不應污染正式數據）。BigQuery：`SUM(value)` 需按 `currency` 分組。

## 4. 內容存取規則（誰能用什麼）

| 使用者狀態 | DIY template | 靜態桌布 |
|---|---|---|
| Premium（訂閱） | 直接套用，`expiresAt = 0`，可存草稿 | `AvailableDownloadPremiumModal` 直接下載，無廣告 |
| 已購買該 item | 同上 | 直接下載 |
| 免費 item（`freeDownload` 或今日限免）且 `freeTrialDays > 0` | `DiyLiveModal` 看一支 Rewarded Ad → trial N 天（Room `diy_unlock_record`） | — |
| 免費 item 且 `freeTrialDays == 0` | 看一支廣告 → 永久（legacy） | `NormalModal` 看廣告 → 下載 |
| 付費 item | `OneTimePurchaseModal` | `NormalModal` 的付費按鈕 → `OneTimePurchaseModal` |
| 花朵 item（`flowerCost > 0`） | `FlowerTrialModal`（`FeatureFlags.FLOWER_SYSTEM_ENABLED = false`，目前退回購買 modal） | — |

`DiyLiveWallpaperSaveButton` 角標：`freeDownload` → 藍色 PlayCircle；需購買 → 黃底鎖頭；trial 生效中 → 滿版漸層背景、不畫角標；premium / 已購買 → 無角標。靜態桌布 `FullscreenScreen` 的套用按鈕角標邏輯鏡射此設計。

## 5. DiyUnlockRecord（解鎖紀錄）

```kotlin
@Entity(tableName = "diy_unlock_record")
data class DiyUnlockRecord(@PrimaryKey val itemId: String, val unlockedAt: Long, val expiresAt: Long) // 0 = 永久
```

DAO：`upsert`、`getByItemId`、`getAllFlow`（收藏頁倒數）、`getAll`（Worker 一次性讀）、`deleteByItemId`（刪草稿連帶撤銷）。

寫入者：
1. 編輯器 `DiyLiveModal.onEarned`（`freeTrialDays > 0`）→ `now + days`。
2. `HeroQuickApply.apply()` 同規則。
3. 收藏頁免費續期（看廣告後）→ `min(max(expiresAt, now) + freeTrialDays, now + maxTrialDays)`。
4. `BillingViewModel.handlePurchase()` → 購買後改 `0`。
5. 花朵兌換 `redeemWithFlowers()`（flag 關閉，不可達）。

每次寫入後都呼叫 `TrialExpiryReminderScheduler.reschedule()`（見 [[projects/PaletteWallAndroid/modules/notifications-and-workers]]）。`expiresAt` 經 `doSaveAndApply()` 寫入 SharedPrefs `expires_at` 供 Service 判斷到期，不進 `template_json`。

## 6. 定價腳本 `scripts/set_onetime_price.py`

- 用途：把 Google Play **所有一次性（managed）商品**設成同一個基準價（例如 `--price 1.99 --currency USD`），由 Google `convertRegionPrices` 自動換算各地區；訂閱不受影響。`--sku` 可限定商品、`--dry-run` 先預覽（列出每個 SKU 的舊→新 US 價、不寫入）。
- 使用新的 Android Publisher `monetization.onetimeproducts` API（舊 `inappproducts` API 已回 403 要求遷移，舊腳本 `set_iap_price.py` 已移除）。
- 需要 Google Cloud 服務帳號 JSON（放在 `scripts/` 旁、已 git-ignore）並在 Play Console 授予定價權限；必須用 `scripts/.venv` 的 python 執行。**本 wiki 不記錄任何 key 或檔案內容。**
- 注意：價格傳播通常幾分鐘、偶爾數小時；自動換算不保證 `.99` 結尾。

## 7. 已知陷阱

- `isPremium` 與 `isAlreadyPurchase` 是兩個概念：前者只看訂閱；UI 判斷「不用付費」要兩者都看。
- `queryPurchases()` 每次啟動都跑，任何「成功」埋點放在 `handlePurchase` 都會每次啟動重複。
- `OneTimePurchaseModal` 的價格 5 秒逾時只是 UI fallback，結帳時 Billing 會重查商品，不會扣錯錢，所以收藏頁可直接用 session 快取價。
- Rewarded Ad 的降級行為是刻意的；要收緊時改呼叫端（例如失敗不發獎），不要改 `RewardedAdState`。
- 2026-07-28 起 `EditDiyLiveWallpaperScreen` 的 SaveAndApply 事件 3 秒去重，只擋 log 不擋動作。
