---
title: PaletteWallAndroid 團隊 / 成長 / 營運資料摘要
source: raw/PaletteWallAndroid/team/（README.md、TEAM_BRIEF.md、growth/、reports/weekly_2026-07-22.md）
updated: 2026-11-24
confidence: high
---

# 團隊 / 成長 / 營運（team/）

本頁整理 `team/` 目錄：AI 團隊的每週迴圈、北極星指標、任務看板、廣告投放、ASO、社群貼文與週報。
數字一律以來源文件所寫為準（註明日期），不自行從 `team/reports/raw/*.csv` 計算。

相關頁：[[projects/PaletteWallAndroid/plans]]（規劃文件）、[[projects/PaletteWallAndroid/modules/retention-and-trial]]、[[projects/PaletteWallAndroid/modules/monetization]]、[[projects/PaletteWallAndroid/overview]]。

---

## 1. 團隊運作方式

### AI 團隊與角色
三個 AI subagent 圍繞每週迴圈運作，自動路由、不用手動呼叫：
- **data-analyst**：數據問題（BigQuery GA4 export）。
- **growth-marketer**：行銷問題（ASO、社群、廣告）。
- **qa-engineer**：commit 前把關；**report-only**（工具清單無 Edit/Write，不會自己改 code）。

### TEAM_BRIEF 是單一事實來源
`team/TEAM_BRIEF.md` 由 `/weekly-report` 每週更新，是三個 agent 與人類工程師的共同看板：北極星指標、本週焦點、工程/行銷任務、廣告投放狀態、更新紀錄。所有 agent 開工前先讀它；專案 CLAUDE.md 也規定「討論成長/營利/該做什麼時先讀這個」。
另一個事實來源是 `team/growth/ads/campaign_state.md`：**實際廣告投放設定的唯一登記檔**（人工維護），agent 的投放建議都以它為現況依據。

### 每週迴圈
```
週一：（投放中才需要）從 Google Ads 匯出上週成效 CSV → growth/ads/exports/
  ↓  /weekly-report   → 查 BigQuery、產出 reports/weekly_YYYY-MM-DD.md、更新 TEAM_BRIEF
  ↓  /ads-readiness   → Ads 成效（CSV）× GA4 用戶品質（週報）交叉 → 層級建議（擴大 / 維持小額 / 暫停）
本週：工程照 TEAM_BRIEF ③ 出貨（qa-engineer 把關）；行銷跑 /social-post、/aso-audit；
      改了 Google Ads 設定就同步更新 campaign_state.md
  ↓  下週一的報告驗證這週改動有沒有推動指標 → 迴圈
```

### Slash commands
| 指令 | 做什麼 | 頻率 |
|---|---|---|
| `/weekly-report` | 六項固定 BigQuery 分析 → 週報 + 更新 TEAM_BRIEF | 每週一 |
| `/ads-readiness` | 廣告投放層級建議 | 每週，跟著週報 |
| `/aso-audit` | 關鍵字研究 + 重建 9 語系商店頁文案 | 每 1–2 月或商店頁改版時 |
| `/social-post` | 各平台社群貼文草稿（可綁本週限免 item） | 每週 |

### 排程與原則
- 主要方式是**每週一早上手動跑 `/weekly-report`**：查詢需要本機 gcloud 使用者憑證，cloud 排程沙箱沒有；選配 macOS launchd 自動執行（跑順兩週後再考慮）。
- 環境：`gcloud` + `bq` CLI、GA4 BigQuery export（延遲 1–2 天）。
- **行銷產出一律 draft-first**：agent 只寫草稿檔，發佈（Play Console / 社群 / Google Ads）由人工執行。
- 廣告策略（2026-07-22 拍板）：維持小額數據收集投放；留存指標只 gate「擴大預算」，不 gate「投不投」。

### 目錄結構
| 路徑 | 內容 |
|---|---|
| `TEAM_BRIEF.md` | 看板（單一事實來源） |
| `reports/weekly_*.md` | 每週數據報告（時間序列靠 git history） |
| `reports/adhoc_*.md` | 臨時深挖分析 |
| `reports/raw/YYYY-MM-DD/` | bq 原始 CSV dump（本 wiki 不讀） |
| `growth/aso/` | 關鍵字研究、listing 草稿 |
| `growth/social/` | 社群貼文草稿 |
| `growth/ads/` | 投放層級建議 + campaign 草稿；`campaign_state.md` 登記檔；`exports/` 每週 Ads CSV（cost 唯一來源） |

---

## 2. 北極星指標與本週焦點（TEAM_BRIEF，週報 2026-07-22；更新紀錄至 2026-07-28）

終極目標：**讓 PaletteWall 持續營利（收益 > 成本）**。基線來自 `doc/growth_assessment_2026-07-11.md` 與 `doc/retention_maximization_plan_2026-07-15.md` §0（見 [[projects/PaletteWallAndroid/plans]]）。

| 指標 | 基線 (2026-07-11) | 本週 (07-14～07-20) | 90 天目標 | 樣本警示 |
|---|---|---|---|---|
| 首日「成功套用桌布」率 | 11% | 12.2%（6/49） | ≥ 35% | n=49 |
| D1 留存 | 11% | 11.4%（5/44） | ≥ 20% | n=44 |
| D7 留存 | ~0% | 0.7%（1/137，cohort 07-07～13） | ≥ 8% | cohort 含 07-10 異常量 |
| 首小時卸載佔比 | 60%（of 57% 總卸載） | 58.3%（of 49% 總卸載） | < 25% | 卸載 n=24，統計上不可信 |
| 自然流量佔比（organic） | 7% | 30.6%（15/49）* | ≥ 30% | *CPC 停投墊高比例，organic 絕對量僅 ~2/天 |
| ARPDAU（`ad_revenue_paid` / DAU） | ~$0 | $0.00018（$0.0184/週） | > $0 且趨勢向上 | 僅 24 筆事件，統計上不可信 |

原則：DAU ~44 的量級下，任何 n < 20 的 cohort 都標「統計上不可信」並降低結論權重。

**本週焦點（週報 2026-07-22）**：新用戶第一小時 activation 仍是最大破口 — 63% 的新用戶（31/49）從未打開 DIY 編輯器、28.6% 首小時內卸載 → E2「首開一鍵套用 fast path」是最該推進的任務；另外 LOCK_TAPPED 10 人 → 完成購買 0 人，付費解鎖漏斗需要健檢。

---

## 3. 工程 / 行銷任務看板（TEAM_BRIEF，狀態截至 2026-07-28）

### 給工程師（依 roadmap Tier）
| # | 任務 | Tier | 驗收指標 | 狀態 |
|---|---|---|---|---|
| E1 | Deep link（`palettewall://`：收藏頁、限免區、單品預覽），通知點擊直達目的地 | 1c | `notification_open` 後到達頁面正確 | 未開始 |
| E2 | Hero 一鍵套用（2026-07-23 重新設計定案；計劃書見 [[projects/PaletteWallAndroid/plans]]） | 1a | 首日成功套用率 12.2% → ≥20%；hero 漏斗建基線 | App 端已實作（07-23，layout B）；阻塞：後端 settings 加 `heroItemId` + 選品上架 |
| E3 | 桌面 Widget（Glance） | 2b | Widget 安裝後 D7 對比 | 未開始 |
| E4 | 分享浮水印 + Play 連結 UTM | 2c | 分享事件帶 UTM、可歸因 | 未開始 |
| E5 | 後端欄位部署（`freeOnDaysOfWeek` / `maxTrialDays` / `serverTimeUtcMs`，見 `doc/free_system_backend_todo.md`） | 後端 | 限免日在 app 正確顯示 | 阻塞中 |

### 給行銷
| # | 任務 | 產出位置 | 狀態 |
|---|---|---|---|
| M1 | ASO 稽核 + 重建 9 語系商店頁文案（`/aso-audit`） | `doc/google_play_listing_and_release_note.md` | 草稿已產出（07-22），發佈待人工 |
| M2 | 每週社群貼文草稿（`/social-post`），配合每週限免輪替 | `team/growth/social/` | 每週 |
| M3 | 廣告投放層級評估（`/ads-readiness`） | `team/growth/ads/` | 每週 |

### 其他定調（更新紀錄 2026-07-23）
Static Wallpaper「保留但凍結新開發」：39.3% 造訪率、static-only D1 13.4% > diy-only 10.0%、banner 收益幾乎全在含 static 的 session；中期做 static→DIY 橋接；缺「static 設為桌布完成」埋點待補。

---

## 4. 廣告投放狀態

### 策略（TEAM_BRIEF ⑤，2026-07-22 使用者拍板）
自然流量太低，不投廣告就收集不到使用者數據 → **維持「小額數據收集」投放**；留存指標只作為擴大預算的門檻。此決定覆蓋 `retention_maximization_plan` 的「D1<20% 不投任何 UAC」鐵律。教訓（07-11 診斷）：之前 76% CPC 流量買在低變現市場（伊朗/南亞），小額也必須買對地區。

擴大三條件（截至 07-28 皆未達成）：D1 ≥ 20%（11.4%）；首小時卸載 < 25%（58.3% of 卸載）；Tier 1 全上線（1b 已做、1a 部分、1c 未開始）。

### readiness_2026-07-22（首次評估）
- 依據週報 07-22。結論：**啟動小額數據收集檔（$5–10/day）**；擴大不考慮（0/3）、暫停不適用（根本沒在跑）。
- 本週 18 個 cpc 歸因是停投前的延遲歸因殘留，不代表現行成效；geo 至少 9 筆落在排除清單（伊朗/印度/孟加拉）→ 新 campaign 的地區設定是最關鍵欄位。
- 草稿設定：UAC App installs、$7/day、投放美/台/日/韓/西歐、明確排除 Iran/India/Pakistan/Bangladesh、事件出價 `diy_purchase_free_SaveAndApply`（不退回純 install 出價）、素材主打「自己的照片 → 動態桌布」。

### campaign_state.md（實際投放登記，狀態截至 2026-07-30）
- **巴西檔**（既有）：2026-07-24 開跑、NT$79/day（≈$2.4）、**Install volume** 出價、僅巴西、語言英/葡 — 與 07-22 草稿不同，屬使用者有意選擇（Android 市占高、CPI 中價位）。GA4 觀察到伊朗/印度少量漏入，判定 VPN 用戶無法防堵。**待人工執行**：暫停（或 7/31 收齊 D7 後暫停）。
- **台灣願付驗證檔**（2026-07-30 建立中）：NT$150/day（≈$4.6）、**In-app actions 事件出價**、目標事件改為 **`diy_purchase_2_CHECKOUT_STARTED`**（已標 Firebase Key event；草稿原訂 `diy_purchase_free_SaveAndApply`，理由：後者只反映免費功能使用、與付款意圖無關）、僅台灣（Location include = Presence）、語言繁中/英、結束日期 **2026-08-25**（停損檢查點）、tCPA/ROAS 留空讓系統學習、View-through conversion 關閉、Audience signal 已設。預期第一週 Limited by data；備案改 `diy_purchase_1_LOCK_TAPPED_SaveAndApply`。**尚待使用者確認是否已送出**。
- 每週人工匯出 Ads CSV（按日 + 按地區）到 `growth/ads/exports/`；未來可用 Google Ads API 自動化（目前不做）。

### readiness_2026-07-28（專項評估：停巴西、建台灣）
- 巴西檔五天（07-23～27）：安裝 36+、CPI 約 $0.27–0.33（匯率估，缺 Ads CSV）、**首日成功套用率 22.2%**（基線 12.2%，視為 E2 生效訊號）、進編輯器 61.1%、D1 13.9%、首小時卸載 63.2%（n=19 不可信）、五天廣告收益 $0.059（回收率 ~0.5%）、IAP 0（5 筆 BRL 結帳全數秒取消）。
- 結論：行為數據任務完成，但**結構上測不到願付意願**（新興市場付款基建缺口，變現缺口約 170 倍）→ 暫停巴西檔、建台灣檔。
- 為什麼台灣：06-28 唯一一筆 TWD 99 成交經確認為**自家測試單**，30 天真實成交 = 0；台灣 Play 付款覆蓋完整（信用卡、電信帳單代扣、超商、ATM、PayPal）；CPI 約 $0.5–1.5；母市場。
- 開跑前置：定價 33 → 分層 **TWD 60（標準）/ 99（Hero/精選）**，開跑後 4 週不改價；購買 modal 加「支援電信帳單、超商付款，免綁卡」文案；Billing 觀測補洞（已完成，見 changelog 2026-07-28）；SaveAndApply 事件去重。
- **停損檢查點 2026-08-25**：CHECKOUT_STARTED ≥30 且完成率 ≥5% → 繼續；完成率 <5% 但慢速取消多 → 降價重測；連 LOCK_TAPPED 都少 → 產品吸引力問題，停投回 organic；硬停損累積 NT$8,000 仍無第 1 筆真實成交 → 無條件暫停。
- 順帶觀察：台灣 cohort 續期行為（單人續期 ≥3 次且 0 購買 → 上「同 item 續期上限 2–3 次」護欄）；hero 漏斗 launched→success 是否重現。

→ 付費與廣告機制見 [[projects/PaletteWallAndroid/modules/monetization]]。

---

## 5. ASO 關鍵字研究重點（keyword_research_2026-07-22）

- 產自 `/aso-audit`；量級/競爭度為**定性**判斷（無 ASO 工具 API），依據 WebSearch 與第三方摘要。
- 目標：自然流量佔比 7% → ≥30%；`自然安裝 = 曝光（ASO 關鍵字）× 商店頁轉換率`，本研究負責曝光端。
- **競品觀察**：
  1. 「live wallpaper maker」大字被 Wave（50M+、4.5★）壟斷 → 不進 title，只放 full description 吃相關性。
  2. 「DIY live wallpaper」是中量級戰場（xWall、Widgify、Collage 系，百萬～五百萬檔），可進 title/short description。
  3. 「photo live wallpaper / my photo wallpaper」意圖最精準、競爭最弱 → **主攻長尾**。
  4. 沒有競品在 listing 主打免費機制（每週限免、30 天試用、看廣告續期）→ short description 差異化 hook。
  5. 沒有人用 before/after（靜態照片 → 動起來）當第一張截圖 → 我們用這個。
- **目標關鍵字（摘錄）**：en：DIY live wallpaper（title + short）、photo live wallpaper、animated wallpaper from photo、turn photos into live wallpaper；zh-TW：動態桌布（title）、照片動態桌布、桌布 DIY/自製桌布；ja：ライブ壁紙、動く壁紙、写真 壁紙；ko：라이브 배경화면、사진 배경화면；es：fondos animados、fondos con tus fotos；另 zh-CN / pt-BR / hi / ar 各 2–3 核心字。
- **文案主軸**：第一句永遠是「你自己的照片 → 有動畫的桌布」；免費機制進 short description 第二句；主力市場（US/TW/JP/KR）做 Play Console custom store listing；每月重跑 `/aso-audit`。
- 成品：`doc/google_play_listing_and_release_note.md`（9 語系，見 [[projects/PaletteWallAndroid/plans]]）。

---

## 6. 社群貼文策略（social_2026-07-22_we-love-cats-free）

- 草稿由 `/social-post` 產出，**需人工審核後發佈**。綁定真實存在的限免 item「We Love Cats」（每週三限免 `freeOnDaysOfWeek: [3]`、7 天 free trial / 最長 30 天）。
- **定位**：不是又一個桌布圖庫 — 把你自己的照片變成有動畫的動態桌布；免費機制（每週限免、30 天試用、看廣告續期）可入文案。
- **平台與格式**：
  - X：≤280 字元、hook 前置、1–2 hashtags、附 10–15 秒短影片。
  - Instagram Reels：caption + 15–30 秒 before→after 腳本（0–3s hook 相簿貓照 → 打開 App 選模板挑照片 → Save & Apply 回主畫面動畫播放（核心 3 秒）→ 慢動作重播 + 字卡）；掛 trending audio。
  - TikTok：口語化 caption、寵物梗 / before-after 轉場 / phone setup tag 圈；商用音樂庫。
  - Reddit（r/androidapps / r/wallpapers）：開發者第一人稱、誠實不像廣告、先讀該版自我宣傳規則；誠實說明免費模式還在摸索、徵求 OEM 相容回饋。
- 每個平台連結帶 UTM（`utm_source` = 平台、`utm_medium=social`、`utm_campaign` = 主題 slug），一週後在 GA4 查 `traffic_source` 看哪個平台帶量；貼文連結回填到草稿檔表格。
- 素材 checklist：直式 1080×1920 螢幕錄影、item thumbnail 動圖、2–3 張可公開的自拍貓照（不用網路圖）、乾淨主畫面截圖。
- 發佈前先確認限免仍有效（非週三就改寫為「每週三免費」）。

---

## 7. 每週報告重點數據（weekly_2026-07-22）

查詢區間 2026-07-14～07-20；**首份報告，無上週對比**，以 2026-07-11 基線比較。全週新增僅 49 人、DAU 均值 ~15，所有 cohort n < 50、多數細分 n < 20 = 統計上不可信。

- 指標總表同第 2 節（首日套用 12.2%、D1 11.4%、D7 0.7%、首小時卸載 58.3% of 卸載、organic 30.6%、ARPDAU $0.00018），趨勢 vs 基線全部持平或假性達標。
- DAU 日序列（07-14→07-20）：20, 18, 13, 7, 16, 20, 10（均值 14.9，下滑通道；07-10 曾有 139 的單日異常尖峰）。
- 新增 49 人中 24 人（49.0%）已卸載；分桶 <1h = 14、1–24h = 6、≥1d = 4；注意右截斷（越晚安裝可觀察天數越短）。
- IAP 本週 **0 筆**完成購買；付費漏斗：鎖定按鈕點擊 10 人 → checkout 2 人 → 取消 3 人 → 完成 0 人；另 1 筆 `diy_purchase_price_load_failed`。
- **最弱環節**：DIY 漏斗 first_open 49 → `diy_edit_screen_opened` 18（36.7%，-63.3% 最大流失點）→ `diy_photo_added_*` 8（16.3%）→ 成功套用 6（12.2%）。7 個新用戶點到上鎖的 SaveAndApply 後 0 人付費解鎖；`diy_exit_edit_page` 新用戶 16 人共 66 次（平均每人退出 3.7 次，編輯器卡點明顯）。
- 建議行動：① 重啟 E2 一鍵套用 fast path；② 挖 `diy_exit_edit_page` 參數；③ E1 deep link 動工（1b 通知已上線，`notification_receive` 已有 4 筆）；④ 付費解鎖漏斗健檢；⑤ 小額數據收集 campaign 依地區教訓重啟；⑥ M1 ASO 稽核（organic 達標是假象，絕對量僅 ~2 人/天）。
- 廣告：UAC 已暫停約 2 週；18 個 cpc first_open 為延遲歸因殘留，geo 仍是舊 campaign 的低變現市場模式。CPC 殘留 / Organic / direct 三組 cohort 品質（n 均 < 20）：CPC D1 16.7%、套用成功 0%；Organic D1 13.3%、首小時卸載 46.7%、套用成功 20.0%；direct D1 0%、套用成功 18.8%。
- 定義備註：「成功套用」= `diy_purchase_free_SaveAndApply` ∪ `free_trial_active_SaveAndApply` ∪ `flower_trial_modal_SaveAndApply`；`diy_purchase_1_LOCK_TAPPED_SaveAndApply` 是意圖事件不計入成功。`ad_revenue_paid` 僅 07-16 起有資料。
- 附錄列出六項分析對應的 raw CSV（`reports/raw/2026-07-22/`，本 wiki 不讀）與 SQL 摘要。

---

## 8. 與其他頁的關聯

- 北極星指標與行動 Tier 的來源：`doc/growth_assessment_2026-07-11.md`、`doc/retention_maximization_plan_2026-07-15.md`、`doc/e2_hero_quick_apply_plan_2026-07-23.md` → [[projects/PaletteWallAndroid/plans]]。
- 免費/trial/續期/到期提醒機制 → [[projects/PaletteWallAndroid/modules/retention-and-trial]]。
- 付費漏斗事件（`diy_purchase_*`）、Billing、AdMob 收益事件 → [[projects/PaletteWallAndroid/modules/monetization]]。
- Hero 一鍵套用 → [[projects/PaletteWallAndroid/modules/diy-live-wallpaper]]。

## 待確認
- 台灣願付驗證檔是否已實際開跑、巴西檔是否已暫停（campaign_state 2026-07-30 仍標待確認）。
- 2026-08-25 停損檢查點的結果（來源中無後續週報）。
- 07-22 之後是否有新的 `weekly_*.md`（來源只有 07-22 一份）。
