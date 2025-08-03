# 自動上下班打卡系統計劃

## 概述
為震旦HR系統 (https://erpline.aoacloud.com.tw) 開發Docker化的自動打卡工具，使用UV管理Python環境，支援GitHub Container Registry部署。

## 目前問題分析
- 需要手動每日上下班打卡，容易遺忘
- 震旦HR系統需要登入驗證和特定操作流程
- 需要可靠的自動化解決方案，支援容器化部署
- 要求支援UV環境管理和GitHub Container Registry

## 策略和方法
1. **技術選型**: 使用Playwright進行網頁自動化（比Selenium更快更穩定）
2. **環境管理**: UV作為Python套件管理器（比pip快10-100倍）
3. **容器化**: Docker多階段建構，優化映像大小
4. **排程**: APScheduler實現靈活的排程配置
5. **部署**: GitHub Actions自動建構並推送到Container Registry

## 實施步驟

### 第一階段：專案基礎設置 ✅
- [✅] 初始化UV專案並配置pyproject.toml
- [✅] 分析震旦HR系統網站結構和登入流程
- [✅] 安裝核心依賴 (playwright, apscheduler等)

### 第二階段：核心功能開發 ⏳
- [✅] 實現基本的網頁自動化邏輯 (登入功能)
- [✅] 建立 AoaCloudPunchClock 主要類別
- [⏳] 實現完整打卡功能邏輯 (上班/下班打卡)
- [✅] 建立配置管理系統 (config.py)
- [✅] 建立資料模型系統 (models.py)
- [✅] 實現視覺化測試系統 (visual_test.py)
- [✅] 建立主程式與測試工具分離架構
- [⏳] 實現排程系統 (APScheduler)
- [⏳] 增強錯誤處理和重試機制

### 第三階段：容器化和部署
- [ ] 撰寫Dockerfile (多階段建構with UV)
- [ ] 建立docker-compose.yml配置
- [ ] 設定GitHub Actions CI/CD管道
- [ ] 建立部署文檔和使用說明

### 第四階段：測試和優化
- [✅] 視覺化測試系統開發
- [✅] 自動截圖和錯誤診斷功能
- [✅] HTML測試報告生成
- [ ] 功能測試和錯誤處理
- [ ] 性能優化和穩定性測試
- [ ] 文檔完善和使用指南

## 時程規劃
- **第一階段**: 1天 (專案設置和分析)
- **第二階段**: 1.5天 (核心功能開發)
- **第三階段**: 1天 (容器化和CI/CD)
- **第四階段**: 0.5天 (測試和文檔)
- **總計**: 4天

## 風險評估
### 潛在風險
1. **網站結構變更**: 震旦HR系統可能更新導致自動化失效
2. **認證機制**: 可能有驗證碼或其他安全機制
3. **網絡問題**: 連線不穩定導致打卡失敗
4. **容器環境**: 無頭瀏覽器在容器中的兼容性問題

### 緩解策略
1. **靈活的選擇器**: 使用多種元素定位策略
2. **錯誤重試**: 實現智能重試機制
3. **狀態檢查**: 驗證打卡成功狀態
4. **通知系統**: 失敗時發送通知
5. **日誌記錄**: 詳細的操作日誌便於除錯

## 成功標準
1. **功能性**: 能成功自動登入並完成打卡
2. **可靠性**: 99%的成功率，具備錯誤恢復能力
3. **可維護性**: 配置簡單，容易部署和更新
4. **容器化**: 成功建構並推送到GitHub Container Registry
5. **文檔完整**: 完整的部署和使用說明

## 進度追蹤

### 專案設置階段 ✅
- [✅] UV專案初始化
- [✅] 網站結構分析
- [✅] 依賴安裝

### 開發階段 ⏳
- [✅] 登入邏輯實現 (AoaCloudPunchClock.login)
- [✅] 基礎自動化框架建立
- [✅] 配置系統完成 (ConfigManager類別)
- [✅] 資料模型定義 (models.py，包含視覺化測試模型)
- [✅] 視覺化測試系統 (VisualTestRunner類別)
- [✅] 自動截圖和錯誤診斷功能
- [✅] HTML測試報告生成
- [✅] 主程式與測試工具分離架構
- [⏳] 打卡邏輯實現 (punch_in/punch_out方法)
- [⏳] 排程系統 (APScheduler整合)
- [⏳] 錯誤處理優化

### 容器化階段
- [ ] Dockerfile撰寫
- [ ] Docker Compose配置
- [ ] GitHub Actions設定

### 測試部署階段
- [✅] 視覺化測試系統實現
- [✅] 自動截圖和錯誤診斷
- [✅] HTML測試報告生成
- [ ] 功能測試
- [ ] 容器測試
- [ ] 文檔撰寫

## 相關檔案
**已完成的檔案：**
- ✅ `pyproject.toml` - UV專案配置
- ✅ `uv.lock` - 鎖定版本檔案
- ✅ `src/punch_clock.py` - 主要打卡邏輯 (AoaCloudPunchClock類別)
- ✅ `src/config.py` - 配置管理 (ConfigManager類別with Pydantic)
- ✅ `src/models.py` - 資料模型定義（包含視覺化測試模型）
- ✅ `src/visual_test.py` - 視覺化測試核心模組
- ✅ `src/__init__.py` - 模組初始化
- ✅ `main.py` - 純粹的主程式入口（僅基本登入測試）
- ✅ `main_visual.py` - 專門的視覺化測試工具
- ✅ `config.example.json` - 配置範本
- ✅ `config.json` - 實際配置檔案

**待完成的檔案：**
- [ ] `src/scheduler.py` - 排程管理
- [ ] `Dockerfile` - 容器建構檔
- [ ] `docker-compose.yml` - 部署配置
- [ ] `.github/workflows/docker-publish.yml` - CI/CD管道
- [ ] `README.md` - 使用說明

## 專案結構優化
**已完成結構重構：**
- ✅ 簡化目錄結構：從 `src/aoacloudpunchio/` 改為 `src/`
- ✅ 優化 import 路徑和模組間依賴
- ✅ 更新 pyproject.toml 配置

**目前專案結構：**
```
/root/python/AoaCloudePunchIO/
├── src/                           # 源碼目錄
│   ├── __init__.py
│   ├── punch_clock.py             # 自動化邏輯（含截圖功能）
│   ├── config.py                  # 配置管理
│   ├── models.py                  # 資料模型（含視覺化測試模型）
│   └── visual_test.py             # 視覺化測試核心
├── main.py                        # 純粹主程式入口
├── main_visual.py                 # 專門視覺化測試工具
├── config.example.json            # 範例配置
├── pyproject.toml                 # 專案配置
└── docs/plan/                     # 規劃文檔
```

## 網站分析結果
**震旦HR系統登入表單識別：**
- 🔍 公司代號欄位：`name='CompId'`, placeholder='公司代號'
- 🔍 帳號欄位：`name='UserId'`, placeholder='帳號'  
- 🔍 密碼欄位：`name='Passwd'`, placeholder='密碼'
- 🔍 登入按鈕：`text='登入'`
- 🔍 目標網址：`https://erpline.aoacloud.com.tw`

**研究和分析檔案：** (位於 `docs/research/`)
- 📊 `analyze_site.py` - 網站分析工具腳本
- 📄 `login_page.html` - 登入頁面HTML結構快照
- 📸 `login_page_analysis.png` - 登入頁面視覺截圖
- 📋 分析工具成功識別所有必要的表單元素和選擇器

---
*最後更新: 2025-08-04*
*狀態: 第一階段完成，第二階段 85% 完成 - 登入功能、核心架構、視覺化測試系統已實現，打卡邏輯和排程系統開發中*

## 最新開發進展 (2025-08-04)

### ✅ 視覺化測試系統完成
**已實現功能:**
- 完整的截圖系統：關鍵步驟自動截圖、錯誤時診斷截圖
- 互動式測試模式：可在每個步驟暫停觀察
- HTML測試報告：包含截圖的可視化測試報告
- 測試統計分析：成功率、執行時間、步驟詳情
- 程式分離架構：主程式與測試工具完全分離

**技術實現:**
- `src/visual_test.py`: VisualTestRunner 類別
- `main_visual.py`: 專門的測試工具入口
- 支援多種輸出格式：JSON、HTML
- 完整的命令行參數系統

**修正問題:**
- UV 環境配置和依賴同步
- Playwright 瀏覽器和系統依賴安裝
- 模組導入路徑修正
- HTML 模板格式化問題修正

## 專案結構設計原則
### 🎯 程式分離架構
**主程式與測試分離**：
- `main.py`：純粹的自動打卡主程式
  - 僅包含基本登入測試
  - 保持簡潔，專注核心功能
  - 生產環境使用的入口點
  
- `main_visual.py`：專門的視覺化測試工具
  - 完整的視覺化測試功能
  - 截圖、報告生成、互動模式
  - 開發和除錯時使用

### ✅ 視覺化測試功能（已完成）
- **截圖功能**: 關鍵步驟自動截圖，錯誤時自動截圖
- **互動模式**: 可在步驟間暫停等待用戶確認
- **測試報告**: 生成包含截圖的HTML視覺化報告
- **測試統計**: 成功率、執行時間、步驟詳情等

### 📋 使用方式
```bash
# 主程式 - 基本自動打卡
uv run python main.py

# 視覺化測試工具
uv run python main_visual.py --show-browser          # 顯示瀏覽器
uv run python main_visual.py --interactive           # 互動模式
uv run python main_visual.py --output-html report.html  # 生成HTML報告

# 完整功能組合
uv run python main_visual.py --show-browser --interactive --output-html report.html --log-level DEBUG
```

## 近期開發重點
1. **完成打卡邏輯**: 實現上班/下班打卡的具體操作流程
2. **排程系統整合**: 使用 APScheduler 實現自動化排程
3. **錯誤處理優化**: 增強重試機制和異常處理
4. **容器化準備**: 開始 Docker 和 CI/CD 相關工作