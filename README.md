# 震旦HR系統自動打卡程式

使用 Python 和 Playwright 開發的網頁自動化打卡系統，專為震旦HR系統 (AoaCloud) 設計，支援GPS定位、排程自動打卡功能。

## 主要功能

- ✅ **自動登入**: 自動填寫帳號密碼並登入系統
- ✅ **GPS定位**: 支援GPS定位功能避免打卡失敗
- ✅ **排程打卡**: 使用 APScheduler 實現定時排程
- ✅ **視覺化測試**: 提供豐富的網頁HTML測試報告
- ✅ **錯誤處理**: 完整的重試機制和錯誤記錄
- ✅ **容器化**: Docker 和 Docker Compose 支援
- ✅ **CI/CD**: GitHub Actions 自動化建構

## 技術架構

### 核心技術
- **Python 3.11+**: 主要開發語言
- **UV**: 套件管理器（比 pip 快 10-100 倍）
- **Playwright**: 網頁自動化框架
- **APScheduler**: 任務排程系統
- **Pydantic**: 資料驗證和設定管理
- **Loguru**: 日誌記錄系統

### 專案結構
```
AoaCloudePunchIO/
├── src/                    # 核心源碼
│   ├── __init__.py
│   ├── punch_clock.py      # 自動化登入和打卡邏輯
│   ├── config.py          # 設定管理系統
│   ├── models.py          # 資料模型定義
│   ├── scheduler.py       # 排程管理系統
│   ├── retry_handler.py   # 錯誤處理和重試機制
│   └── visual_test.py     # 視覺化測試系統
├── main.py               # 主程式入口
├── main_visual.py        # 視覺化測試工具
├── config.example.json   # 設定檔範例
├── Dockerfile           # 容器化設定
├── docker-compose.yml   # Docker Compose 設定
└── docs/               # 文件目錄
    ├── plan/          # 專案規劃
    └── research/      # 研究分析
```

## 快速開始

### 1. 環境需求

確保系統已安裝：
- Python 3.11 或更高版本
- Git

### 2. 安裝 UV 套件管理器

```bash
# macOS 或 Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用 pip
pip install uv
```

### 3. 專案設置

```bash
# 複製專案
git clone https://github.com/your-username/AoaCloudePunchIO.git
cd AoaCloudePunchIO

# 安裝依賴
uv sync

# 安裝 Playwright 瀏覽器
uv run playwright install chromium
```

### 4. 設定檔設置

```bash
# 複製設定檔範例
cp config.example.json config.json

# 編輯設定檔填入您的資訊
nano config.json
```

設定檔內容：
```json
{
  "login": {
    "company_id": "您的公司代號",
    "user_id": "您的使用者帳號",
    "password": "您的密碼"
  },
  "schedule": {
    "clock_in_time": "09:00",
    "clock_out_time": "18:00",
    "enabled": true,
    "weekdays_only": true
  },
  "gps": {
    "latitude": 25.0330,
    "longitude": 121.5654,
    "address": "台北市"
  },
  "debug": false,
  "headless": true
}
```

## 使用方式

### 基本測試
```bash
# 執行基本登入測試
uv run python main.py

# 視覺化測試（顯示瀏覽器）
uv run python main_visual.py --show-browser --interactive
```

### 實際打卡
```bash
# 執行上班打卡
uv run python main.py --real-punch --sign-in

# 執行下班打卡
uv run python main.py --real-punch --sign-out
```

### 排程執行
```bash
# 啟動排程系統（根據設定自動打卡）
uv run python main.py --schedule
```

### 視覺化測試選項
```bash
# 生成HTML測試報告
uv run python main_visual.py --output-html report.html

# 互動式測試（顯示瀏覽器）
uv run python main_visual.py --interactive --show-browser

# 除錯模式
uv run python main_visual.py --show-browser --log-level DEBUG
```

## 使用 Docker 部署

### 使用 Docker Compose（推薦）

```bash
# 啟動排程系統
docker-compose up -d

# 查看日誌
docker-compose logs -f punch-scheduler

# 停止系統
docker-compose down
```

### 直接 Docker 部署

```bash
# 建立映像
docker build -t aoacloud-punch:latest .

# 執行容器
docker run -d \
  --name punch-scheduler \
  -v $(pwd)/config.json:/app/config.json:ro \
  -v $(pwd)/logs:/app/logs \
  aoacloud-punch:latest
```

## 進階設定

### 環境變數設定

您也可以使用環境變數來設定：

```bash
export COMPANY_ID="your_company_id"
export USER_ID="your_user_id"
export PASSWORD="your_password"
```

### 排程設定

在 `config.json` 中調整排程時間：

```json
{
  "schedule": {
    "clock_in_time": "08:30",
    "clock_out_time": "17:30",
    "enabled": true,
    "weekdays_only": true
  }
}
```

### GPS 定位設定

```json
{
  "gps": {
    "latitude": 25.0330,
    "longitude": 121.5654,
    "address": "台北市信義區"
  }
}
```

## 開發和貢獻

### 開發環境設置

```bash
# 安裝開發依賴
uv sync --dev

# 執行程式碼品質檢查
uv run ruff check src/
uv run ruff format src/

# 執行型別檢查
uv run mypy src/
```

### 測試開發

```bash
# 基本設定測試
uv run python -c "
import sys
sys.path.insert(0, 'src')
from config import config_manager
config_manager.load_config()
"

# 模組導入測試
uv run python -c "
import sys
sys.path.insert(0, 'src')
from punch_clock import AoaCloudPunchClock
from scheduler import scheduler_manager
"
```

## 主要 API 介面

### 核心類別

#### `AoaCloudPunchClock`
核心打卡自動化類別

```python
from src.punch_clock import AoaCloudPunchClock

async with AoaCloudPunchClock(headless=True) as clock:
    await clock.login(credentials)
    await clock.navigate_to_punch_page()
    result = await clock.execute_real_punch_action(action)
```

#### `PunchScheduler`
排程管理類別

```python
from src.scheduler import scheduler_manager

await scheduler_manager.initialize(punch_callback)
status = scheduler_manager.scheduler.get_job_status()
```

#### `VisualTestRunner`
視覺化測試類別

```python
from src.visual_test import VisualTestRunner

runner = VisualTestRunner(show_browser=True)
result = await runner.run_full_test()
```

## 常見問題排除

### 常見問題

1. **Playwright 瀏覽器安裝失敗**
   ```bash
   # 重新安裝瀏覽器
   uv run playwright install chromium
   uv run playwright install-deps
   ```

2. **設定檔格式錯誤**
   ```bash
   # 驗證設定檔格式
   python -c "import json; json.load(open('config.json'))"
   ```

3. **Docker 權限問題**
   ```bash
   # 修正檔案權限
   sudo chown -R 1000:1000 logs/ screenshots/
   ```

## 安全性注意事項

### 資料安全
- 設定檔中不要硬編碼敏感資訊
- 使用環境變數管理帳號密碼
- 確保設定檔案權限正確

### 網路安全
- 僅連接信任的HR系統
- 使用 HTTPS 連線
- 定期檢查網站憑證有效性

### 系統安全
- 不以 root 使用者執行
- 確保日誌檔案權限安全
- 定期更新依賴套件

## 日誌和監控

### 日誌格式
```
2024-01-01 09:00:00 | INFO | 開始執行排程打卡: sign_in
2024-01-01 09:00:05 | SUCCESS | 打卡完成: sign_in - 上班打卡成功
```

### 監控項目
- 打卡成功率
- 執行錯誤
- 網路狀況
- 系統效能

## 參與貢獻

1. Fork 專案
2. 建立功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 建立 Pull Request

### 程式碼規範
- 使用 Ruff 進行程式碼格式化
- 使用 mypy 進行型別檢查
- 遵循專案既有的程式碼風格
- 為新功能添加適當的測試

## 授權條款

本專案使用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案

## 相關資源

- [Playwright](https://playwright.dev/) - 網頁自動化框架
- [UV](https://github.com/astral-sh/uv) - 快速 Python 套件管理器
- [APScheduler](https://apscheduler.readthedocs.io/) - 任務排程 Python 函式庫
- [Pydantic](https://pydantic-docs.helpmanual.io/) - 資料驗證和設定管理

## 技術支援

如果遇到問題，請按照以下步驟：
1. 查看常見問題排除章節
2. 建立新的 [Issues](https://github.com/Madfater/AoaCloudePunchIO/issues)
3. 詳細描述 Issue 和問題
4. 參與 [Discussions](https://github.com/Madfater/AoaCloudePunchIO/discussions) 討論

---

**重要提醒**: 本工具僅供學習和自動化效率提升使用，請確保使用符合公司政策和相關法規要求。