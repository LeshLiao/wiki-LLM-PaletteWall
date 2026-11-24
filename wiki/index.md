# Wiki Index

每頁一行：`[[路徑]] — 一句話摘要`。查詢時先從這裡找。

## projects/PaletteWallAndroid

Android 桌布 App（靜態桌布 + DIY Live Wallpaper）。來源：raw/PaletteWallAndroid。

- [[projects/PaletteWallAndroid/overview]] — 產品定位、技術棧、build variants、入口點（Application / MainActivity / Manifest）、repo 結構
- [[projects/PaletteWallAndroid/architecture]] — Clean Architecture 三層與 service/di/util、資料流範例、Hilt module、導航路由、ViewModel 清單、三種開關、八條工程鐵律、已知裝置行為
- [[projects/PaletteWallAndroid/api]] — 22 個後端端點總表、x-app-key 驗證機制與 soft/hard 模式、Retrofit 設定、分頁與錯誤處理、Firebase 角色與 R2 遷移、dev/admin 端點
- [[projects/PaletteWallAndroid/data-model]] — Room 7 張 table 與 migration 歷史、SharedPrefs 清單、DTO ↔ domain 對應、DiyTemplate 序列化規則、圖片快取層
- [[projects/PaletteWallAndroid/plans]] — 12 份規劃文件摘要與狀態、changelog 時間軸、35 條決策總表
- [[projects/PaletteWallAndroid/team]] — AI 團隊每週迴圈、北極星指標、工程/行銷看板、廣告投放狀態、ASO、社群、週報數據

### modules

- [[projects/PaletteWallAndroid/modules/diy-live-wallpaper]] — DIY 動態桌布端到端：template → 編輯器 → Room/SharedPrefs → WallpaperService；fraction 座標、Compose↔Service 一致性、動畫系統、draw loop 鐵律、Registry、Dev 工具、Hero Quick Apply、新增欄位 checklist
- [[projects/PaletteWallAndroid/modules/monetization]] — Google Play Billing（訂閱/一次性）、AdMob banner 與 rewarded 解鎖、收益記錄、DiyUnlockRecord、內容存取規則
- [[projects/PaletteWallAndroid/modules/retention-and-trial]] — 免費/試用系統（每週限免、30 天 trial、續期、TrustedTime）、花朵系統封存、到期提醒、InAppReview 與回饋觸發、onboarding
- [[projects/PaletteWallAndroid/modules/home-and-browsing]] — HomeScreen 結構與路由、Live/Static 分頁、搜尋與色彩篩選、收藏、下載套用、Settings/語言、圖片載入與快取
- [[projects/PaletteWallAndroid/modules/notifications-and-workers]] — FCM 推播、通知 opt-in、WorkManager 到期提醒、更新 banner / 強制更新、網路狀態檢查
