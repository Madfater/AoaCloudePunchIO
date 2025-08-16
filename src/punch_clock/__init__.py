"""
打卡模組
震旦HR系統自動打卡功能的完整實現

主要組件:
- PunchClockService: 主要服務接口，提供統一的打卡流程執行接口
- BrowserManager: 瀏覽器管理器，處理瀏覽器初始化和清理
- AuthHandler: 認證處理器，處理登入流程
- NavigationHandler: 導航處理器，處理頁面導航
- PunchExecutor: 打卡執行器，處理真實和模擬的打卡操作
- StatusChecker: 狀態檢查器，檢查頁面狀態和按鈕可用性
- ResultVerifier: 結果驗證器，驗證打卡操作結果
- ScreenshotManager: 截圖管理器，處理截圖功能

使用範例:
```python
from src.punch_clock import PunchClockService
from src.models import LoginCredentials, PunchAction

# 創建登入憑證
credentials = LoginCredentials(
    company_id="your_company",
    user_id="your_user",
    password="your_password"
)

# 初始化服務
service = PunchClockService(
    headless=True,
    enable_screenshots=True,
    interactive_mode=False
)

# 執行打卡操作
result = await service.execute_punch_flow(
    credentials=credentials,
    action=PunchAction.SIGN_IN,
    mode="simulate"  # 或 "real" 或 "visual"
)
```
"""

from .service import PunchClockService
from .browser import BrowserManager
from .auth import AuthHandler
from .navigation import NavigationHandler
from .executor import PunchExecutor
from .checker import StatusChecker
from .verifier import ResultVerifier
from .screenshot import ScreenshotManager

__all__ = [
    'PunchClockService',
    'BrowserManager',
    'AuthHandler',
    'NavigationHandler',
    'PunchExecutor',
    'StatusChecker',
    'ResultVerifier',
    'ScreenshotManager'
]

# 版本資訊
__version__ = '2.0.0'
__author__ = 'AoaCloud Team'
__description__ = '震旦HR系統自動打卡模組'