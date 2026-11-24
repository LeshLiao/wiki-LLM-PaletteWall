---
title: PaletteWallAndroid 規劃與決策文件摘要
source: raw/PaletteWallAndroid/doc/（不含 doc/diy/）
updated: 2026-11-24
confidence: high
---

# 規劃與決策文件摘要（doc/）

本頁整理 `doc/` 底下的規劃、決策與營運文件（`doc/diy/` 的 DIY 子系統設計文件另見 [[projects/PaletteWallAndroid/modules/diy-live-wallpaper]]）。
狀態判定依據：各文件自身的狀態標頭 + `doc/changelog.md`；不確定者標「待確認」。

相關頁：[[projects/PaletteWallAndroid/overview]]、[[projects/PaletteWallAndroid/architecture]]、[[projects/PaletteWallAndroid/api]]、[[projects/PaletteWallAndroid/data-model]]、[[projects/PaletteWallAndroid/team]]。

## 文件總覽

| 文件 | 日期 | 性質 | 狀態 |
|---|---|---|---|
| `doc/instructions.md` | 無日期 | 架構規範（給 AI 工具） | 長期有效 |
| `doc/flower_retention_and_trial_plan.md` | 2026-07-08～07-10 | 花朵收集 retention + DIY 限時免費 | 已實作，之後封存（feature flag 關閉） |
| `doc/firebase_to_r2_migration_plan.md` | 2026-07-10 | 圖檔儲存遷移 | Phase 0–4 已完成，Phase 5 待確認 |
| `doc/growth_assessment_2026-07-11.md` | 2026-07-11 | 成長數據診斷 | 分析報告（行動落到後續文件） |
| `doc/free_system_redesign_plan.md` | 2026-07-14 | 免費系統改版 | client 已實作；後端欄位待確認 |
| `doc/free_system_backend_todo.md` | 2026-07-14 | 後端 TODO（prompt） | 待實作（待確認） |
| `doc/api_token_auth.md` | 2026-07-15 | API 驗證 | Phase 1–2 已實作；Phase 3 hard mode 待確認 |
| `doc/retention_maximization_plan_2026-07-15.md` | 2026-07-15 | Retention 行動方案 | 進行中（1b 已做，其餘多數未做） |
| `doc/google_play_listing_and_release_note.md` | 2026-07-22 | 商店頁文案（9 語系） | 草稿，待人工發佈 |
| `doc/e2_hero_quick_apply_plan_2026-07-23.md` | 2026-07-23 | Hero 一鍵套用 | App 端已實作；後端 heroItemId + 選品待確認 |
| `doc/tester_note.md` | 無日期（內容到 2026-07-24） | 測試技巧 | 長期有效 |
| `doc/ios_port_plan_2026-08-05.md` | 2026-08-05 | iOS 移植分析 | 規劃 |
| `doc/changelog.md` | 2026-07-08～08-06 | 日期開發筆記 | 持續更新 |

---

## instructions.md（無日期）

**背景**：給 Cursor / AI 工具的程式碼生成規範，定義本專案的技術棧與分層規則。

**重點**：
- 技術棧：Kotlin、Jetpack Compose、MVVM + Clean Architecture、Hilt、Retrofit、Coroutines/Flow、Room、AdMob/Google Pay、Firebase Storage/Remote Config、Bitrise CI。
- 三層：Domain（use case、domain model、repository 介面，不得 import Android framework）／Data（Retrofit service、Room DAO、DTO、mapper `Dto.toDomain()`，實作 repository）／Presentation（Compose UI + Hilt ViewModel + UI state/actions，不得知道 Retrofit 或 Room）。
- 文件在 package 結構處截斷（原檔內容未完）。

**狀態**：長期有效的規範；實際分層見 [[projects/PaletteWallAndroid/architecture]]。

---

## flower_retention_and_trial_plan.md（2026-07-08，持續更新至 07-10）

**要解決的問題**：留存極低，且 DIY live wallpaper「看一支廣告永久解鎖」的廣告收益太薄。原檔由 `free_for_one_month_plan.md` 擴充更名而來。

**方案**：
1. **花朵代幣**：看一支 Rewarded Ad = 領當日獎勵，存本地 Room `flower_basket`（單列、上限 24 朵），首頁右上角計數器。
2. **農場頁連續簽到**（`FarmScreen`）：原 3 天制 Day1/2/3 = 1/2/3 朵，2026-07-09 改 7 天制（Day1=1、Day2..6=3、Day7=7），漏一天重置；每次領取都要看廣告；另有獨立的「每日開花」24h 冷卻獎勵與 App 更新獎勵。
3. **花朵兌換取代看廣告解鎖 trial**：後端 item 帶 `flowerCost`/`freeTrialDays`；`FlowerTrialModal` 兩選項「🌸N 免費 30 天」或「購買永久」；扣花與 `diy_unlock_record` upsert 同一 Room transaction。
4. **到期偵測在 Service 本地比對**：`DiyWallpaperConfig.save()` 加 `expiresAt`（SharedPrefs，不進 `template_json`）；`DiyLiveWallpaperService` 在 `onVisibilityChanged` 判定、到期畫「桌布已到期」overlay，不開 App、不需網路，遵守 draw loop 禁 allocation。
5. Room v7→v8（`diy_unlock_record`、`flower_basket`），之後 v8→v9（`lastBloomAt`）、v9→v10（`rewardedVersionCode`）。
6. 收藏頁 trial 倒數 bar + 續期 pill；`DiyWallpaperConfig.updateExpiresAt()` 同步套用中桌布。
7. 網路檢查：`NetworkUtil.isNetworkAvailable()`（要求 `NET_CAPABILITY_VALIDATED`）擋「飛航模式白嫖」。
8. P6 Welcome 全螢幕 overlay（後於 07-10 改成 ExoPlayer 影片 hero）。

**明確不做（v1）**：靜態桌布 trial（系統 intent 後 App 無控制權）、後端花朵錢包、防改時鐘對帳、到期推播。

**狀態**：client P1–P6 於 2026-07-08～07-10 全部實作；但 **2026-07-14 free system redesign 以 `FeatureFlags.FLOWER_SYSTEM_ENABLED = false` 將整套花朵系統封存**（程式碼與 Room 表保留）。到期偵測、`DiyUnlockRecord`、收藏頁倒數 bar 等基礎設施沿用。後端 `flowerCost`/`freeTrialDays` 欄位：`freeTrialDays` 後續被免費系統沿用；`flowerCost` 是否仍在後端 — 待確認。

→ 細節見 [[projects/PaletteWallAndroid/modules/retention-and-trial]]、資料表見 [[projects/PaletteWallAndroid/data-model]]。

---

## firebase_to_r2_migration_plan.md（2026-07-10）

**要解決的問題**：圖檔放 Firebase Storage，下載頻寬隨使用者線性計費且無 CDN；實測約 2,232 檔 / ~986 MB，其中 `images/thumbnail` 平均 429 KB 比 HD 還大，是頻寬大宗。

**方案**：
1. 搬到 **Cloudflare R2**（egress 免費、Standard 10 GB 免費儲存）+ 自訂網域 `cdn.palettex.ca` 走 Cloudflare CDN（Cache Rule edge TTL 30 天、browser 7 天）；不用 `*.r2.dev`。
2. 物件 key 沿用現有 `blob` 路徑，URL 只換 host、去掉 `?alt=media&token=`。
3. Phase 0 Cloudflare 設定 → Phase 1 Super Slurper 搬檔 → Phase 2 MongoDB URL 改寫（先 dump 備份，dry-run 腳本）→ Phase 3 App 端 → Phase 4 上傳工具鏈 → Phase 5 觀察 90 天後清 Firebase。
4. App 必改：`ImageCacheList.extractFileName()`（原本解析 URL-encoded Firebase 格式，不改則內建快取全 MISS、流量反增）、`Material3Carousel` 5 個寫死 URL、dev 上傳改走後端 presigned URL（`POST /api/dev/upload-url`，金鑰不進 APK）、移除 `firebase-storage-ktx`。
5. `scripts/diy/common.py` 由 `firebase_admin` 改 boto3。
6. 附帶建議：縮圖轉 WebP、列表優先用 LD/SD、DB 長期改存 blob-only。

**狀態**：Phase 0–4 於 2026-07-12～07-13 完成（R2 2,371 物件、改寫 2,227 筆 URL / 357 份文件、流量已切到 CDN、`ImageCacheList` 雙格式解析 + unit test）。發現 Cloudflare 會擋 `Python-urllib` UA（OkHttp/Coil/requests 不受影響）。**待辦**：Render 後端加 R2 相關環境變數並部署（未部署前 dev 上傳 endpoint 404）、Phase 5 清 Firebase — 是否已完成：待確認。

→ API 端點與驗證見 [[projects/PaletteWallAndroid/api]]。

---

## growth_assessment_2026-07-11.md（2026-07-11）

**背景**：以 BigQuery GA4 export（2026-06-21～07-09）+ Crashlytics 診斷自然流量與收益路徑。

**關鍵數據**：新增 359 人、cpc 佔 76%、Play 自然流量僅 7%；D1 留存 11%；卸載 57%、其中 60% 在安裝後 1 小時內；前五大國家為伊朗/韓國/印度/巴基斯坦/孟加拉（伊朗無法用 Play Billing/AdMob 變現）；付費漏斗 145 modal → 52 checkout → 47 取消 → 1 購買；Welcome 頁 10 秒倒數鎖 CTA 造成 37% 直接離開；DIY 漏斗僅 11% 成功套用桌布。

**結論與路線圖**：
1. 目前靠付費廣告買到低留存、無法變現的市場，負面訊號反而拖累 Play 自然推薦 → **先修留存 → 再衝 ASO → 最後才重開廣告**。
2. 第 0 步止血廣告（暫停或改鎖可變現市場 + 事件出價）。
3. 第 1 步修首小時體驗：Welcome 倒數改掉、縮短 time-to-value（首開直接一鍵套用精選免費桌布）。
4. 第 2 步 ASO：重建 `google_play_listing_and_release_note.md`、主打低競爭精準關鍵字、首屏截圖展示「自己的照片變動態桌布」。
5. 第 3 步花朵 retention 推滿量驗證；第 4 步修付費漏斗（地區定價）；第 5 步 In-App Review；第 6 步盯 Android vitals；第 7 步每週數據迴圈。
6. 鐵律：**D1 留存沒站上 20% 之前，投廣告 = 燒錢買負面訊號**（後於 2026-07-22 被 TEAM_BRIEF 策略覆蓋，見 [[projects/PaletteWallAndroid/team]]）。

**狀態**：分析報告；行動落到 `retention_maximization_plan_2026-07-15.md` 與 team/ 的每週迴圈。

---

## free_system_redesign_plan.md（2026-07-14）

**要解決的問題**：花朵系統觸及人數太少無法驗證、複雜度高；需要更直接的免費機制：每週限免、免費 = 限時 trial、免費續期。

**方案**：
1. **每週限免**：item 新欄位 `freeOnDaysOfWeek: List<Int>`（ISO 1..7 多日陣列，空 = 無；07-14 由單日 Int 改為陣列），當天首頁顯示 FREE tag，等同 `freeDownload`。
2. **免費 = trial**：免費取得的 live wallpaper 一律限時 `freeTrialDays` 天；收藏頁 progress bar 分母改 `maxTrialDays`（新欄位，default 30）。
3. **免費續期**：不需花朵，每次 +30 天（07-23 起改為 +`freeTrialDays`），上限 `maxTrialDays`；07-19 起續期需看一支 Rewarded Ad。
4. **TrustedTime**（`util/TrustedTime.kt`）：`items/settings/init` 回傳 `serverTimeUtcMs`，App 記 `(serverTime, elapsedRealtime)` 錨點，改時鐘無效；**只用於「今天星期幾」判定**，trial 到期/倒數/Service 維持裝置時鐘；取不到時間或重開機未 sync → `todayDayOfWeek() = 0` **fail-closed**（限免日不生效，無裝置時鐘 fallback）。
5. **花朵系統封存**：`FeatureFlags.FLOWER_SYSTEM_ENABLED = false` 包住所有入口，不刪碼、不做破壞性 migration。
6. Gating 順序：已購買/premium → trial 生效中 → `isFreeNow` 看廣告（`freeTrialDays > 0` 先 upsert unlock record）→ 花朵 modal（flag 關閉跳過）→ 購買 modal。
7. Service 零修改（Rule 5）。
8. 首頁新增「Free Today / 今日限免」置頂群組。

**決策表（摘錄）**：防改時鐘不是為了防使用者延長 trial（回撥時鐘延長屬接受行為）；星期判定用裝置本地時區；`freeTrialDays == 0` 的免費 item 維持永久；靜態桌布不做 trial。

**狀態**：client 端 2026-07-14 全部實作（含 07-15 收藏頁改版、07-19 廣告續期、07-23 trial 天數動態化等後續迭代）。**後端欄位（`freeOnDaysOfWeek`/`maxTrialDays`/`serverTimeUtcMs`）是否上線：待確認**（TEAM_BRIEF 2026-07-28 仍列 E5「阻塞中」；但 07-22 社群貼文草稿已引用某 item 的 `freeOnDaysOfWeek: [3]`，可能表示後端已部分支援）。

→ [[projects/PaletteWallAndroid/modules/retention-and-trial]]、[[projects/PaletteWallAndroid/modules/monetization]]。

---

## free_system_backend_todo.md（2026-07-14）

**背景**：免費系統改版的後端待辦，整段可直接餵給後端 AI / 工程師的自包含 prompt。

**內容**：
1. `GET /api/live_items` 每個 item 加 `freeOnDaysOfWeek`（int array，寫入驗證 1–7 並去重）與 `maxTrialDays`（int，client 視 `<= 0` 為 30）。
2. `GET items/settings/init` 加 `serverTimeUtcMs`（回應當下 UTC epoch ms；**此端點不可被 CDN/快取層快取舊值**，否則 TrustedTime 失效）。
3. §2b（07-23 追加）：settings 加 `heroItemId`（空 = 隱藏 Hero 區塊，兼作遠端 kill switch；該 item 應 `freeDownload: true`）。
4. DIY Wallpaper Manager 頁加 7 個星期 checkbox + `maxTrialDays` 輸入；提醒限免 item 必須同時設 `freeTrialDays > 0`，否則走 legacy 永久免費。
5. `diy_review` staging 流程要持久化新欄位。
6. 相容性：全部 additive，舊版 App 忽略新欄位；新版 App 對舊後端自動 fallback。
7. 附驗收 checklist 與部署後 App 端驗證步驟。

**狀態**：文件標「待實作」（2026-07-14）；實際是否已部署：待確認（同上節）。

→ [[projects/PaletteWallAndroid/api]]。

---

## api_token_auth.md（2026-07-15）

**要解決的問題**：後端寫入端點（`POST/PATCH/DELETE /api/live_items`、`/api/items`、`/api/assets`、`/api/diy_review`、`PUT /api/google-play/onetime/:id`）原本完全無驗證，任何人知道 URL 就能刪改資料庫。

**方案**：static API key 雙軌制。
1. **Admin key**（`x-api-key` header）：保護所有寫入/admin 端點（Tier A），立即硬性強制；永不進 release APK 或 web bundle；過渡期也接受舊 dev upload key。
2. **App key**（`x-app-key` header，`BuildConfig.APP_API_KEY`）：識別 App 讀取流量（Tier B）；可輪替（逗號分隔多把）；定位是「提高門檻」不是機密。
3. `x-app-version` header 帶 versionCode，供後端統計新舊版流量。
4. 後端 `APP_AUTH_MODE` = off / soft（放行 + 記 log，預設）/ hard（401）；改 env 即生效 = 回滾機制。hard mode 放行條件：valid app key 或 Origin 在白名單（web 前端）。
5. Tier C 不驗證：users/orders(PayPal)/items transaction 等 web 商店流程。
6. **不用 Firebase App Check / Play Integrity**：對個人專案過度工程；middleware 集中在單一檔案，日後要升級只改 `appKeyAuth`。
7. 分階段 rollout：Phase 1 後端 Tier A hard + Tier B soft → Phase 2 新版 App 帶 `AuthInterceptor` 上架 → Phase 3（2–6 個月後，無 key 流量 < 5%）切 hard；壓低舊版占比靠 `latestVersionCode` 橫幅 + `minVersionCode` 強制更新 dialog → Phase 4 選配 Play Integrity。
8. App 端關鍵檔：`data/remote/AuthInterceptor.kt`、`di/NetworkModule.kt`、`data/remote/RetrofitInstance.kt`（dev 畫面用，另掛 dev key interceptor）、`app/build.gradle.kts`（`local.properties` 優先、fallback env；**Bitrise 必須設 secret env，否則 release 帶空 key**）。
9. Key 輪替/外洩處理流程。

**狀態**：Phase 1–2 於 2026-07-15 實作並本地驗證（soft + hard）；強制更新機制同日實作。Phase 3 是否已切 hard：待確認。

→ [[projects/PaletteWallAndroid/api]]。

---

## retention_maximization_plan_2026-07-15.md（2026-07-15）

**背景**：`growth_assessment` 的行動續篇。盤點後發現 App 已有「回訪理由」（每週限免、trial 到期、免費續期），但**完全沒有「回訪提醒」管道**（無 WorkManager/AlarmManager 本地排程、無 Widget、無 deep link）。

**北極星指標（90 天目標）**：首日成功套用率 11% → ≥35%；D1 11% → ≥20%；D7 ~0 → ≥8%；首小時卸載佔比 60% → <25%。

**方案（Tier 排序）**：
- **Tier 1**：1a 修首小時體驗（Welcome 倒數改 ≤3 秒或可跳過；一鍵套用 fast path 不逼新用戶進編輯器；挖 `diy_exit_edit_page`）；**1b 本地排程通知（WorkManager）— 最重要**（trial 到期前提醒、限免日早上提醒、到期後撈回，每週 ≤2 則）；1c Deep link（`palettewall://`）。
- **Tier 2**：2a FCM topic 週播「本週限免」；2b 桌面 Widget（Glance）；2c 分享浮水印 + Play 連結 UTM；2d 輕量 7 格週簽到（掛在領免費桌布上，不復活農場）。
- **Tier 3 廣告**：停 UAC；重啟三條件 D1 ≥ 20%、首小時卸載 < 25%、Tier 1 全上線；重啟時鎖定美/台/日/韓/西歐 + 事件出價 + 小預算。
- **Tier 4 商店端**：ASO 重建、首屏截圖 before/after、In-App Review 時機、Android vitals。
- **不做清單**：復活花朵農場、Interstitial / App-open 廣告、低價地區 cpc、騷擾式通知、完整邀請系統。
- 90 天執行順序表（W1 停 UAC + Welcome → W1–2 通知 + deep link → W2–3 一鍵套用 → W3–4 FCM 週播 + 分享 → W5–8 Widget + 簽到 + ASO → W9–12 看數據才重啟廣告）。

**狀態**：進行中。1b 第 1 項（trial 到期前 3 天通知，收藏頁 toggle，`TrialExpiryReminderScheduler` + `TrialExpiryReminderWorker`）於 2026-07-19 實作；1a 的一鍵套用先以 v1 實作（07-15）後 revert（07-19），再以 E2 Hero 重新設計（07-23）；Welcome 於 07-23 改版為 StartedGuidePage（移除倒數鎖）。1c deep link、2a–2d 依 TEAM_BRIEF（07-28）仍未開始。「D1<20% 不投廣告」鐵律於 2026-07-22 被團隊策略覆蓋（維持小額數據收集投放）。

→ [[projects/PaletteWallAndroid/modules/retention-and-trial]]、[[projects/PaletteWallAndroid/team]]。

---

## google_play_listing_and_release_note.md（2026-07-22）

**背景**：`growth_assessment` 第 2 步要求重建的商店頁文案文件（原索引指向的檔案曾不存在，07-11 移除索引、07-22 由 `/aso-audit` 重建）。關鍵字依據 `team/growth/aso/keyword_research_2026-07-22.md`。

**內容**：
1. 9 語系（en / zh-TW / zh-CN / ja / ko / es / pt-BR / hi / ar，對應 `res/values-*`）的 title（≤30）、short description（≤80）、full description（≤4000），字元數逐條驗證。
2. 文案主軸：第一句永遠是「你自己的照片 → 有動畫的動態桌布」；short description 帶每週限免 + 30 天試用 hook；full description 前 3 行塞主關鍵字；迴避與 Wave 在「live wallpaper maker」大字正面對撞。
3. 8 張截圖 shot list（第 1 張 before/after）+ 15–30 秒預覽影片腳本。
4. Release notes 模板（≤500 字元，9 語系）。
5. 人工發佈步驟與 checklist（Draft-only，一律人工進 Play Console）。
6. Store Listing Experiment 建議：一次只測一個變因，先測第一張截圖，再測 icon。

**狀態**：草稿；是否已發佈到 Play Console：待確認。

→ [[projects/PaletteWallAndroid/team]]（ASO 關鍵字研究）。

---

## e2_hero_quick_apply_plan_2026-07-23.md（2026-07-23）

**要解決的問題**：週報 07-22 顯示 63% 新用戶（31/49）從未打開 DIY 編輯器、首日成功套用率 12.2%、首小時卸載 58.3%；「套用桌布」被鎖在產品最深的功能後面。取代 2026-07-15 的 v1 quick-apply（Free Today 每張卡都有按鈕，07-19 revert）。

**v1 的教訓 → 本版**：入口改為首屏最上方**獨立 Hero 區塊只放一支**；選品改「不依賴個人照片也成立」的 template；assets 在 **App 首開即背景 prefetch**（使用者看引導頁時下載完）→ 點套用秒開系統預覽；選擇數只有一張。

**實作清單**：
1. settings 加 `heroItemId`（空 = 隱藏，遠端開關）；App `AppSettings` 同名欄位。
2. Prefetch：首次進入且 heroItemId 非空 → 背景 `PreloadDiyAssetsUseCase`，失敗靜默、點擊時走進度條 fallback。
3. Hero UI（`HeroQuickApplySection.kt`，layout B：左 9:20 動畫卡 + 右文案/CTA）插在 Free Today 之前。
4. 套用管線撿回 revert 的零件：`launchLiveWallpaperPreview()`（三段 OEM fallback）、`DiyQuickApply.apply()` → 新檔 `HeroQuickApply.kt`。
5. 埋點：`hero_quick_apply` → `hero_quick_apply_launched` → `hero_apply_success`（ON_RESUME 時 WallpaperManager 確認 service 生效）；thumbnail 點擊進編輯器記 `hero_thumbnail_click`。
6. 選品：上架一支 hero template（待人工）。

**07-24 調整**：Hero「立即套用」改走**與編輯器相同的 trial 規則**（原計畫「永久免費不進 trial」被推翻）；移除套用成功後的 DIY 橋接 dialog；`HERO_ITEM_ID` 固定在 App 端 `HomeScreen.kt`，後端 `heroItemId` 非空時優先。

**驗收指標**：首日成功套用率 12.2% → ≥20%（90 天 35%）；首小時卸載 < 40%；hero 漏斗建基線。巴西檔 cohort（07-23～27）首日套用率 22.2%，被視為 E2 生效訊號。

**狀態**：App 端 2026-07-23 已實作、07-24 調整；後端 `heroItemId` 與選品上架：待確認。

→ [[projects/PaletteWallAndroid/modules/diy-live-wallpaper]]、[[projects/PaletteWallAndroid/modules/retention-and-trial]]。

---

## tester_note.md（無日期，內容更新至 2026-07-24）

**背景**：收錄「為了快速驗證某功能需要臨時改程式碼」的做法；測完務必還原，不可 commit。

**內容**：
1. 測試花朵試用到期畫面：三個寫入點把一天 `86_400_000L` 改 `60_000L`（`EditDiyLiveWallpaperScreen.redeemWithFlowers()`、看廣告免費試用分支、`LikeCollectionScreen` 續期）。
2. 測試連續簽到：方法 A 改裝置日期（只能往前調，DAO guard 防回撥）；方法 B `FarmViewModel` 三處改 `System.currentTimeMillis() / 60_000L`（還原後必須清 App 資料）。
3. 測試強制更新 Dialog：本地後端改 `minVersionCode` 或 `HomeViewModel.forceUpdateRequired` 恆 true；驗證 back/點外部關不掉、更新按鈕 fallback 開 Play Store。
3b. 測試 E2 Hero 一鍵套用：`HERO_ITEM_ID` 為固定值非 hack，直接改常數即可；驗證劇本含斷網 fallback。
4. 測試 trial 到期前 3 天通知：`TrialExpiryReminderScheduler` 的 `REMINDER_LEAD_MS` 改 40 天、`MIN_DELAY_MS` 改 10 秒 → toggle 開啟後約 10 秒觸發；用 Background Task Inspector 看 `trial_reminder_<itemId>` 任務。
5. Build 指令一律 `./gradlew assembleProdDebug`。

**狀態**：長期有效的測試手冊。

---

## ios_port_plan_2026-08-05.md（2026-08-05）

**背景**：盤點 202 個 Kotlin 檔後回答三個問題：iOS 該怎麼實作、功能要怎麼調整、如何讓 AI agent 自主移植。

**結論**：
1. **最大架構斷點：iOS 沒有動態桌布 API**（無 WallpaperService 對等物，App 不能程式化設定桌布）。產品形態改為：動畫離線渲染成影片 → 轉 Live Photo → 存相簿 → 教學引導使用者手動設鎖屏桌布（iOS 17+ 喚醒時播放）。
2. 技術選型：**原生 Swift + SwiftUI**；不建議 Flutter/RN；KMP 列二期選項。跨平台共用的是「規格」（後端 API、template JSON、R2 assets、渲染規格）而非程式碼。
3. 天然優勢：Android `Phase.ANIMATING → PAUSING`（播一次定格）語意與 Live Photo 吻合，靜態 HEIC = 動畫結束幀。
4. **試用到期機制必須重新設計**：匯出後 App 管不到 → 改「匯出前把關」（試用中匯出加浮水印、購買後無浮水印），商業模式從「租用桌布」變「購買匯出權」。
5. 渲染引擎：純函式 `AnimationEvaluator` + 預覽 renderer + 匯出 renderer（CGContext 逐幀 30fps → AVAssetWriter .mov + HEIC → Live Photo 配對）；必須逐條照搬 CLAUDE.md Critical Rules（fraction 座標系、easing、圖層順序、序列化相容、第二階段動畫）。
6. Live Photo 實務上限約 3 秒 → template 動畫總長需 cap 或 time-scale。
7. 一期不移植：Dev 工具鏈、花朵系統、Widget。
8. 里程碑 M0 規格萃取 → M1 渲染核心 → M2 資料層 → M3 編輯器 → M4 首頁與商店 → M5 完成度 → M6 上架。
9. **Agent Harness**：新 repo `spec/`（rendering_spec / template_schema / api_contract / feature_parity + golden frames）為唯一事實來源、`PORTING_STATUS.md` 任務看板（每 task 附可機器驗證的驗收條件）、**golden-frame 像素比對測試**讓 agent 自我驗證、`ios-qa` / `parity-reviewer` subagent、`/port-next` skill。
10. 風險：Live Photo 配對 metadata 非正式 API、手動設定桌布轉換率低於 Android 一鍵套用、ATT 拒絕率高影響 rewarded eCPM。

**狀態**：規劃；是否已啟動（規格萃取、建 iOS repo）：待確認。

---

## 略提：DIY 流程與資料流文件

- `doc/diy_live_wallpaper_workflow.md`：端到端 mermaid 流程圖（DevTemplateBuilder 建 template → 存 DB → 上傳後端 → 首頁 GET → 編輯器 → Service 渲染），每步列主要檔案。
- `doc/diy_live_wallpaper_data_flow.md`：每個 config 欄位（`PhotoCardConfig`、`DecorationConfig`…）在 Dev Editor / Dev DB / Domain / API JSON / Canvas-Service / Duplicate-to-DB 各階段是否保留的對照表，由 `diy-template-reviewer` agent 維護，用來抓欄位被 drop 的問題。

兩者屬 DIY 子系統設計，詳見 [[projects/PaletteWallAndroid/modules/diy-live-wallpaper]]。

---

## changelog 時間軸（doc/changelog.md 重點）

> 2026-07-07 文件重整：CLAUDE.md 的日期章節全部移入 `doc/diy/*.md`，此後日期筆記只寫 changelog。

| 日期 | 重大變更 |
|---|---|
| 2026-07-08 | 花朵收集 retention + DIY 限時免費 client 實作（Room v7→v8、農場頁、`FlowerTrialModal`、Service 到期 overlay）；修離線白嫖（`NetworkUtil`）；花朵視覺統一；兌換流程改版 + 收藏頁 trial 倒數 bar；P6 Welcome overlay |
| 2026-07-09 | 農場每日開花獎勵（DB v8→v9）；簽到改 7 天制；App 更新獎勵（DB v9→v10）；Firebase 廣告獎勵事件改名定版 |
| 2026-07-10 | Welcome 頁改 ExoPlayer 影片 hero；導航黑屏修復（`popBackStackSafe`）；**桌布圖層消失修復**（Service 冷啟動 ext 猜錯 → ext-agnostic 快取掃描）；DIY tips 輪播；後端 `latestVersionCode` 更新 banner |
| 2026-07-12 | AdMob `ad_revenue_paid` 事件（`AdRevenueLogger`）；`notifications_enabled` user property；R2 Phase 0–1 |
| 2026-07-13 | R2 Phase 2–4：DB URL 改寫切到 CDN、`ImageCacheList` 雙格式、dev 上傳改 presigned、移除 `firebase-storage-ktx`、scripts 換 boto3 |
| 2026-07-14 | **Free System Redesign client 全實作**（花朵系統封存、`freeOnDaysOfWeek`、`TrustedTime`、免費 = trial、免費續期）；限免改多日陣列 + Free Today 群組；隱藏首頁輪播；修 `AnimatedImageDrawable` NPE；Welcome 體驗修正、DIY 縮圖重播間隔 |
| 2026-07-15 | 收藏頁大改版（分頁、滿寬續期/購買按鈕、刪草稿撤銷 trial）+ Service overlay 加 icon；**API token 驗證三邊同步**；**強制更新機制**（`minVersionCode` + `ForceUpdateDialog`）；retention 行動方案文件；v1 quick-apply（`ef6783f`） |
| 2026-07-19 | revert v1 quick-apply；收藏頁續期改看廣告；**trial 到期前 3 天通知**（WorkManager，retention 1b）；購買完成清除 trial 倒數；CopyTo Card transform 單向同步；還原底部 banner 廣告；暫時隱藏 Welcome |
| 2026-07-23 | E2 Hero 計劃書 + 實作（layout B）；**StartedGuidePage**（Welcome + 3 頁輪播，移除倒數鎖）；trial 天數動態化；**Billing Library 8.0.0** + Kotlin 2.0.21 / Hilt 2.51.1；**targetSdk 36** + AGP 8.9.0 / Gradle 8.14.3（Play 2026-08-31 政策） |
| 2026-07-24 | E2 Hero 調整：改走 trial 規則、移除 DIY 橋接 dialog、事件改名（`hero_apply_success`）、`HERO_ITEM_ID` 固定在 App 端 |
| 2026-07-28 | 付費漏斗觀測補洞：`diy_purchase_3_LAUNCH_FAILED`、price load failed 帶 error_code、SaveAndApply 事件 3 秒去重；備註 06-28 唯一成交為開發者測試單 |
| 2026-08-06 | **DIY 第二階段動畫（Phase 2）**：`AnimPhase2`、`rest*` extensions、`totalDurationMs()`、Builder Phase2 sub-tab、END2 拖曳點 |

---

## 決策總表

| 決策 | 日期 | 理由 | 出處 |
|---|---|---|---|
| 只對 DIY live wallpaper 做 trial，靜態桌布不做 | 2026-07-08 | 靜態桌布走系統 intent、原圖已在 Downloads，App 無控制權 | flower_retention_and_trial_plan |
| 到期偵測用 Service 本地時間比對、不用網路/WorkManager/FCM | 2026-07-08 | Service 被系統保活、每次亮屏 `onVisibilityChanged`，最可靠且符合 Rule 5 | flower_retention_and_trial_plan |
| 花籃獨立 entity + SQL 原子條件 UPDATE | 2026-07-08 | 避免 `user_settings` 讀整列→REPLACE 的 lost update | flower_retention_and_trial_plan |
| 廣告 no-fill 仍給獎（降級），但 request 前先檢查網路 | 2026-07-08 | 不讓 fill rate 斷 streak；同時擋飛航模式白嫖 | flower_retention_and_trial_plan |
| retention 事件一律 `flower_` 前綴 | 2026-07-08 | 命名一致、BigQuery 好查 | flower_retention_and_trial_plan |
| 圖檔遷移 Cloudflare R2 + 自訂網域 CDN，不用 Cloudflare Images | 2026-07-10 | egress $0、免費額度內月費 $0、順帶全球 CDN | firebase_to_r2_migration_plan |
| Firebase 檔案保留至少 90 天不刪 | 2026-07-10 | 保護舊 JSON 快取與 rollback | firebase_to_r2_migration_plan |
| R2 金鑰不進 APK，dev 上傳走後端 presigned URL | 2026-07-10 | 金鑰安全 | firebase_to_r2_migration_plan |
| 先修留存 → ASO → 才重開廣告；D1<20% 不投 UAC | 2026-07-11 / 07-15 | cpc 買到低變現市場、餵 Play 負面訊號 | growth_assessment、retention_maximization_plan |
| Welcome 頁倒數鎖 CTA 要改掉 | 2026-07-11 | 37% 使用者在倒數期間直接離開 | growth_assessment |
| AdMob 收益用 `OnPaidEventListener` 自記 `ad_revenue_paid` | 2026-07-12 | AdMob↔Firebase 連結不匯出金額到 BigQuery | changelog |
| 花朵系統以 feature flag 封存，不刪碼、不做破壞性 migration | 2026-07-14 | 「暫時保留」需求；flag 比大段註解乾淨 | free_system_redesign_plan |
| TrustedTime 只用於星期判定，trial 到期維持裝置時鐘 | 2026-07-14 | 防改時鐘是為限免日正確，不是防延長 trial | free_system_redesign_plan |
| 取不到 server time → 限免日 fail-closed，無裝置時鐘 fallback | 2026-07-14 | 寧可少送限免也不給假冒空間；離線本來也看不了廣告 | free_system_redesign_plan |
| `freeOnDayOfWeek: Int` 改 `freeOnDaysOfWeek: List<Int>` | 2026-07-14 | JSON array 免解析、Manager 多選 checkbox 直接對應、MongoDB `$in` 友善 | free_system_redesign_plan / changelog |
| API 驗證用 static key 雙軌，不用 App Check / Play Integrity | 2026-07-15 | 個人專案過度工程；middleware 集中可日後升級 | api_token_auth |
| App key 讀取流量先 soft 觀察數月再切 hard | 2026-07-15 | 舊版 App 零影響、env 切換即回滾 | api_token_auth |
| `minVersionCode` 值必須 ≤ Play 全量發布版本 | 2026-07-15 | staged rollout 期間調高會鎖死所有使用者 | changelog |
| 不做 Interstitial / App-open 廣告 | 2026-07-15 | 直接傷留存與卸載率 | retention_maximization_plan |
| 不復活花朵農場，簽到改輕量版掛在領免費桌布上 | 2026-07-15 | 數據未驗證、複雜度高 | retention_maximization_plan |
| 收藏頁續期改看 Rewarded Ad | 2026-07-19 | 免費 + 無廣告變現太弱（原 v2 方案） | free_system_redesign_plan / changelog |
| revert v1 quick-apply（Free Today 每卡按鈕） | 2026-07-19 | 純 UX 決策（原因未詳記，計劃書標註） | changelog / e2 plan |
| 到期提醒改「前 3 天」、預設 OFF、放收藏頁 toggle | 2026-07-19 | 需通知權限、避免騷擾 | changelog |
| 維持小額數據收集投放；留存只 gate 擴大預算 | 2026-07-22 | organic 太低不投收不到數據；覆蓋 07-15 鐵律 | team/TEAM_BRIEF（見 [[projects/PaletteWallAndroid/team]]） |
| ASO 迴避「live wallpaper maker」大字，主攻 photo/DIY 長尾 | 2026-07-22 | Wave 50M+ 壟斷大字 | google_play_listing / keyword_research |
| E2 改為首屏獨立 Hero 區塊只放一支、首開 prefetch | 2026-07-23 | activation 階段選擇是敵人；進度條是最大流失點 | e2_hero_quick_apply_plan |
| Static Wallpaper 保留但凍結新開發 | 2026-07-23 | 39.3% 造訪率、static-only D1 高於 diy-only、banner 收益集中 | team/TEAM_BRIEF |
| 不升 Billing 9.x | 2026-07-23 | 需 Kotlin 2.2，等下次 toolchain 升級 | changelog |
| Hero 改走與編輯器相同 trial 規則（推翻永久免費） | 2026-07-24 | 使用者拍板 | changelog |
| 移除 Hero 套用後 DIY 橋接 dialog | 2026-07-24 | 使用者決定不要此步驟；thumbnail 點擊已進編輯器 | changelog |
| 06-28 TWD 99 成交為測試單，轉換分析排除 | 2026-07-28 | 真實成交 = 0 | changelog / readiness_2026-07-28 |
| 第二階段動畫靜止終態一律用 `rest*` 不用 `end*` | 2026-08-06 | phase2 可改終值 | changelog |
| iOS 用原生 Swift + SwiftUI，產品形態改 Live Photo 匯出 | 2026-08-05 | iOS 無動態桌布 API | ios_port_plan |
| iOS 試用改「匯出前把關」（浮水印） | 2026-08-05 | 匯出後 App 管不到 | ios_port_plan |
