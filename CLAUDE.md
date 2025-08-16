# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Commit Message Convention

Follow the conventional commit format:
```
<type>: <description>

Examples:
- feat: add new product API endpoint
- fix: resolve order status mapping issue
- docs: update API documentation
- refactor: restructure data transformers
- test: add order controller tests
- style: format code according to rubocop
- chore: update dependencies
```

**Common types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `style`: Code style changes
- `chore`: Maintenance tasks

## Documentation and Planning Requirements

### Mandatory Documentation for Major Changes
When implementing any significant module changes, feature additions, or architectural modifications, you MUST create and maintain documentation in the `docs/plan/` directory.

#### Required Documentation Process
1. **Create Planning Document**: Before starting any major modification, create a detailed plan document in `docs/plan/[feature-name]-plan.md`
2. **Document Progress**: Update the plan document with progress status as work progresses
3. **Maintain Both Tracking Systems**: Use both in-memory todo lists AND persistent documentation

#### Plan Document Structure
```markdown
# [Feature/Change Name] Plan

## Overview
Brief description of the change and its purpose

## Current Problem Analysis
Detailed analysis of what needs to be changed and why

## Strategy and Approach
How the change will be implemented

## Implementation Steps
Detailed breakdown of tasks with priorities and status

## Timeline
Expected completion dates for each phase

## Risk Assessment
Potential risks and mitigation strategies

## Success Criteria
How to measure successful completion

## Progress Tracking
Real-time status updates (✅ ✓ ⏳ ❌)

## Related Files
List of all files that will be modified
```

#### When to Create Plan Documents
- New feature implementations
- Architectural refactoring (like removing v1 dependencies)
- Database schema changes
- API version migrations
- Security enhancements
- Performance optimizations
- Major bug fixes that affect multiple components

#### Documentation Maintenance
- Update progress markers in real-time as tasks complete
- Record any deviation from original plan with reasoning
- Document lessons learned and implementation notes
- Keep status current for team visibility

This ensures that all major work is properly tracked, documented, and can be resumed by anyone on the team.

## 專案特定指導方針

### 震旦HR系統自動打卡專案
這是一個使用 Playwright 進行網頁自動化的打卡系統專案。

#### 核心技術棧
- **Python 3.11+**: 主要開發語言
- **UV**: 套件管理器（比pip快10-100倍）
- **Playwright**: 網頁自動化（比Selenium更穩定）
- **APScheduler**: 任務排程
- **Pydantic**: 資料驗證和設定管理
- **Loguru**: 日誌記錄

#### 專案結構
```
src/                    # 核心源碼
├── __init__.py         # 模組初始化
├── punch_clock.py      # 自動化登入和打卡邏輯
├── config.py          # 配置管理系統
├── models/            # 資料模型定義（分離架構）
│   ├── __init__.py     # 統一導出接口
│   ├── core.py        # 核心打卡相關模型
│   ├── config.py      # 配置相關模型
│   └── testing.py     # 測試相關模型
├── visual_test.py     # 視覺化測試核心模組
└── scheduler.py       # 排程管理（待開發）

docs/
├── plan/              # 專案規劃文檔
│   └── auto-punch-clock-plan.md # 主要開發計畫
└── research/          # 研究和分析檔案
    ├── analyze_site.py       # 網站分析工具
    ├── login_page.html       # 登入頁面HTML快照
    └── login_page_analysis.png # 頁面截圖

.env                   # 實際環境變數設定檔（基於 .env.example）
main.py               # 統一主程式入口點（整合所有功能）
```

#### 開發原則
1. **安全優先**: 不在代碼中硬編碼憑證，使用環境變數進行配置
2. **錯誤處理**: 實現重試機制和詳細的錯誤日誌
3. **資源管理**: 使用異步上下文管理器確保瀏覽器資源正確清理
4. **配置分離**: 支援開發、測試、生產環境的不同配置

#### 震旦HR系統技術細節
- **目標網址**: `https://erpline.aoacloud.com.tw`
- **登入表單識別**:
  - 公司代號: `input[name="CompId"]`
  - 使用者帳號: `input[name="UserId"]` 
  - 密碼: `input[name="Passwd"]`
  - 登入按鈕: `button:has-text("登入")`

#### 設定和配置
**環境變數設定**:
- 複製 `.env.example` 為 `.env`: `cp .env.example .env`
- 修改 `.env` 文件中的必要設定值（COMPANY_ID, USER_ID, PASSWORD）
- 所有敏感資料都使用環境變數，不會被提交到版本控制

**必要環境變數**:
- `COMPANY_ID`: 震旦HR系統公司代號
- `USER_ID`: 使用者帳號
- `PASSWORD`: 登入密碼

**可選環境變數**（有預設值）:
- `CLOCK_IN_TIME`: 上班打卡時間（預設: 09:00）
- `CLOCK_OUT_TIME`: 下班打卡時間（預設: 18:00）
- `SCHEDULE_ENABLED`: 是否啟用排程（預設: true）
- `WEEKDAYS_ONLY`: 僅工作日執行（預設: true）
- `GPS_LATITUDE`, `GPS_LONGITUDE`, `GPS_ADDRESS`: GPS 定位設定
- `DEBUG`: 除錯模式（預設: false）
- `HEADLESS`: 無頭瀏覽器模式（預設: true）

#### 測試和驗證
**基本測試**:
- 使用 `uv run python main.py` 進行基本登入功能測試
- 確保 `.env` 配置正確（基於 `.env.example`）
- 測試前務必確認網站結構未變更

**視覺化測試**:
- 使用 `uv run python main.py --visual --show-browser` 觀看自動化過程
- 使用 `uv run python main.py --visual --interactive` 進行互動式測試
- 使用 `uv run python main.py --visual --output-html report.html` 生成測試報告

#### 部署考量
- 支援 Docker 容器化部署
- 使用無頭瀏覽器模式適應服務器環境
- 配置 GitHub Actions 自動建構和部署

#### 當前開發狀態
**已完成功能**:
- ✅ 基礎專案架構和配置管理
- ✅ 震旦HR系統登入自動化
- ✅ 使用 Playwright 的穩定網頁自動化
- ✅ 環境變數配置管理系統 (.env)
- ✅ 資料模型定義 (Pydantic)
- ✅ 網站結構分析和元素識別
- ✅ 完整的視覺化測試系統
- ✅ 自動截圖和錯誤診斷功能
- ✅ HTML測試報告生成
- ✅ 互動式測試模式
- ✅ 主程式與測試工具分離架構

**開發中功能**:
- ⏳ 實際打卡操作邏輯
- ⏳ 任務排程系統 (APScheduler)
- ⏳ 錯誤處理和重試機制優化

**待開發功能**:
- ❌ Docker 容器化
- ❌ GitHub Actions CI/CD 管道
- ❌ 完整的部署文檔

#### 主要檔案功能說明
- **src/punch_clock.py**: 包含 `AoaCloudPunchClock` 類別，實現網站自動化邏輯和截圖功能
- **src/config.py**: 使用 Pydantic 和環境變數進行配置驗證和管理
- **src/models/**: 分離式資料模型架構，包含核心、配置、測試相關模型
- **src/visual_test.py**: 視覺化測試執行器，支援截圖、報告生成、互動模式
- **main.py**: 統一程式入口點，整合所有功能（基本打卡、視覺化測試、排程器）

#### 統一入口架構設計
**功能整合**:
- `main.py`: 統一所有功能的主入口點，支援基本打卡、視覺化測試、排程器模式

**命令使用方式**:
```bash
# 基本功能
uv run python main.py                          # 模擬測試
uv run python main.py --real-punch             # 真實打卡
uv run python main.py --schedule               # 排程器模式

# 視覺化測試
uv run python main.py --visual                                # 基本視覺化測試
uv run python main.py --visual --show-browser                 # 顯示瀏覽器
uv run python main.py --visual --interactive                  # 互動模式
uv run python main.py --visual --output-html report.html     # 生成報告
uv run python main.py --visual --real-punch --show-browser   # 視覺化真實打卡
```

## Memories

### Project Memories
- Learned the importance of separating configuration from code in the Aoacloud Punch IO project
- Successfully implemented web automation using Playwright for HR system login
- Developed a robust configuration management system using Pydantic
- **2025-08-04**: 成功實現完整的視覺化測試系統
  - 實現了主程式與測試工具的分離架構
  - 添加了自動截圖和錯誤診斷功能
  - 建立了HTML測試報告生成系統
  - 修正了UV環境配置和模組導入問題
  - 確保了Playwright瀏覽器環境的正確安裝
  - 重構配置系統改為使用 .env 環境變數管理，提升安全性和部署便利性