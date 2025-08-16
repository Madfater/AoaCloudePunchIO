# 自動打卡程式

使用 Python 和 Playwright 開發的網頁自動化打卡系統，支援 GPS 定位、排程自動打卡功能。

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
│   ├── punch_clock/        # 打卡服務模組
│   │   ├── service.py      # 主要服務接口
│   │   ├── browser.py      # 瀏覽器管理
│   │   ├── auth.py         # 認證處理
│   │   └── ...            # 其他專門模組
│   ├── models/            # 資料模型
│   ├── config.py          # 設定管理系統
│   ├── scheduler.py       # 排程管理系統
│   └── retry_handler.py   # 錯誤處理和重試機制
├── main.py               # 主程式入口（包含所有功能）
├── .env.example         # 環境變數範例檔案
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

### 4. 環境變數設置

```bash
# 複製環境變數範例檔案
cp .env.example .env

# 編輯環境變數檔案填入您的資訊
nano .env
```

環境變數設定內容：
```bash
# 基本登入資訊
COMPANY_ID=您的公司代號
USER_ID=您的使用者帳號
PASSWORD=您的密碼

# 排程設定
CLOCK_IN_TIME=09:00
CLOCK_OUT_TIME=18:00
SCHEDULE_ENABLED=true
WEEKDAYS_ONLY=true

# GPS 定位設定
GPS_LATITUDE=25.0330
GPS_LONGITUDE=121.5654
GPS_ADDRESS=台北市

# 系統設定
DEBUG=false
HEADLESS=true
```

## 使用方式

### 基本測試
```bash
# 執行基本登入測試
uv run python main.py

# 視覺化測試（顯示瀏覽器）
uv run python main.py --visual --show-browser --interactive
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
uv run python main.py --visual --output-html report.html

# 互動式測試（顯示瀏覽器）
uv run python main.py --visual --interactive --show-browser

# 除錯模式
uv run python main.py --visual --show-browser --log-level DEBUG
```

## 使用 Docker 部署

### 使用 Docker Compose（推薦）

```bash
# 1. 確保 .env 檔案存在並正確設定
cp .env.example .env
nano .env  # 編輯環境變數

# 2. 啟動排程系統
docker-compose up -d

# 3. 查看日誌
docker-compose logs -f punch-scheduler

# 4. 停止系統
docker-compose down
```

**重要**: 確保 `.env` 檔案與 `docker-compose.yml` 在同一目錄，系統會自動將環境變數檔案掛載到容器內。

### Docker 權限問題解決

如果在 Docker 容器中遇到截圖或日誌寫入權限問題，請嘗試以下解決方案：

#### 方案 1: 設定正確的用戶 ID（推薦）
```bash
# Linux/macOS 系統
export USER_ID=$(id -u) 
export GROUP_ID=$(id -g)
docker-compose up -d --build
```

#### 方案 2: 修正宿主機目錄權限
```bash
# 給予截圖和日誌目錄適當權限
sudo chmod 777 ./screenshots ./logs
docker-compose up -d
```

#### 方案 3: 檢查權限狀態
```bash
# 運行權限檢查工具
docker-compose run --rm punch-test /app/check_permissions.sh

# 或直接運行權限檢查腳本
./scripts/check_permissions.sh
```

#### 方案 4: 使用 root 模式（不推薦用於生產環境）
在 `docker-compose.yml` 中註釋掉以下行：
```yaml
# user: "${USER_ID:-1000}:${GROUP_ID:-1000}"
```

### 直接 Docker 部署

```bash
# 建立映像
docker build -t ghcr.io/madfater/aoacloudepunchio:latest .

# 執行容器
docker run -d \
  --name punch-scheduler \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  ghcr.io/madfater/aoacloudepunchio:latest
```

## 進階設定

### 環境變數設定

本專案使用環境變數進行配置管理，提供更好的安全性：

```bash
# 設定必要的環境變數
export COMPANY_ID="your_company_id"
export USER_ID="your_user_id"
export PASSWORD="your_password"

# 或使用 .env 檔案管理
cp .env.example .env
# 編輯 .env 檔案填入您的設定
```

### 排程設定

在 `.env` 檔案中調整排程時間：

```bash
# 排程設定
CLOCK_IN_TIME=08:30
CLOCK_OUT_TIME=17:30
SCHEDULE_ENABLED=true
WEEKDAYS_ONLY=true
```

### GPS 定位設定

```bash
# GPS 定位設定
GPS_LATITUDE=25.0330
GPS_LONGITUDE=121.5654
GPS_ADDRESS=台北市信義區
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
print('✅ 配置系統正常')
"

# 模組導入測試
uv run python -c "
import sys
sys.path.insert(0, 'src')
from punch_clock import AoaCloudPunchClock
from scheduler import scheduler_manager
from models import PunchAction
print('✅ 模組載入正常')
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

#### 視覺化測試
統一的打卡服務接口

```python
from src.punch_clock import PunchClockService
from src.models import LoginCredentials

# 創建登入憑證
credentials = LoginCredentials(
    company_id="your_company",
    user_id="your_user", 
    password="your_password"
)

# 創建服務並執行視覺化測試
service = PunchClockService(
    headless=False,           # 顯示瀏覽器
    enable_screenshots=True,  # 啟用截圖
    interactive_mode=True     # 互動模式
)

# 執行視覺化測試
result = await service.execute_punch_flow(credentials, None, "visual")

# 生成報告
service.generate_html_report(result, Path("report.html"))
service.save_json_report(result, Path("result.json"))
```

## 常見問題排除

### 常見問題

1. **Playwright 瀏覽器安裝失敗**
   ```bash
   # 重新安裝瀏覽器
   uv run playwright install chromium
   uv run playwright install-deps
   ```

2. **環境變數設定錯誤**
   ```bash
   # 檢查環境變數是否正確載入
   uv run python -c "from src.config import config_manager; config_manager.load_config(); print('環境變數載入成功')"
   ```

3. **Docker 權限問題**
   ```bash
   # 方案1: 設定正確的用戶 ID（推薦）
   export USER_ID=$(id -u) && export GROUP_ID=$(id -g)
   docker-compose up -d --build
   
   # 方案2: 修正目錄權限
   sudo chmod 777 ./screenshots ./logs
   
   # 方案3: 使用權限檢查工具
   ./scripts/check_permissions.sh
   docker-compose run --rm punch-test /app/check_permissions.sh
   
   # 方案4: 檢查容器內權限狀態
   docker-compose exec punch-scheduler ls -la /app/
   ```

4. **截圖功能失敗**
   ```bash
   # 檢查瀏覽器權限和共享記憶體
   docker-compose logs punch-scheduler | grep "permission\|shm\|screenshot"
   
   # 增加共享記憶體大小（在 docker-compose.yml 中）
   shm_size: '2gb'
   ```

5. **容器啟動失敗**
   ```bash
   # 檢查容器啟動日誌
   docker-compose logs punch-scheduler
   
   # 檢查權限和掛載點
   docker-compose run --rm punch-test /app/check_permissions.sh
   
   # 除錯模式啟動
   docker-compose run --rm punch-test bash
   ```

## 安全性注意事項

### 資料安全
- 使用 .env 檔案管理敏感資訊
- 確保 .env 檔案不被提交到版本控制
- 確保環境變數檔案權限正確（600）

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

## CI/CD 管道

本專案使用 GitHub Actions 實現自動化建構和部署：

### 工作流程包含
- ✅ **程式碼品質檢查**: Ruff 和 mypy
- ✅ **Docker 建構**: 自動建構多平台映像 (linux/amd64, linux/arm64)
- ✅ **安全掃描**: Trivy 漏洞掃描
- ✅ **自動部署**: 推送到 GitHub Container Registry

### 映像標籤格式
```bash
# 主要映像
ghcr.io/madfater/aoacloudepunchio:latest

# 分支映像
ghcr.io/madfater/aoacloudepunchio:master

# 版本標籤 (當建立 release 時)
ghcr.io/madfater/aoacloudepunchio:v1.0.0
```

### 使用預建映像
```bash
# 直接使用預建映像
docker pull ghcr.io/madfater/aoacloudepunchio:latest
docker run -d --env-file .env ghcr.io/madfater/aoacloudepunchio:latest
```

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