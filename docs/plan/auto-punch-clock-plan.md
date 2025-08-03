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
- [⏳] 實現打卡功能邏輯
- [✅] 建立配置管理系統
- [ ] 實現排程系統 (APScheduler)

### 第三階段：容器化和部署
- [ ] 撰寫Dockerfile (多階段建構with UV)
- [ ] 建立docker-compose.yml配置
- [ ] 設定GitHub Actions CI/CD管道
- [ ] 建立部署文檔和使用說明

### 第四階段：測試和優化
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
- [✅] 登入邏輯實現
- [⏳] 打卡邏輯實現
- [✅] 配置系統
- [ ] 排程系統

### 容器化階段
- [ ] Dockerfile撰寫
- [ ] Docker Compose配置
- [ ] GitHub Actions設定

### 測試部署階段
- [ ] 功能測試
- [ ] 容器測試
- [ ] 文檔撰寫

## 相關檔案
**已完成的檔案：**
- ✅ `pyproject.toml` - UV專案配置
- ✅ `uv.lock` - 鎖定版本檔案
- ✅ `src/punch_clock.py` - 主要打卡邏輯
- ✅ `src/config.py` - 配置管理
- ✅ `main.py` - 主程式入口和測試功能
- ✅ `config.example.json` - 配置範本

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
│   ├── punch_clock.py             # 自動化邏輯
│   └── config.py                  # 配置管理
├── main.py                        # 主程式入口
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

---
*最後更新: 2025-08-04*
*狀態: 第一階段完成，第二階段進行中*