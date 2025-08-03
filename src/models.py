"""
資料模型統一定義模組
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel


class LoginCredentials(BaseModel):
    """登入憑證資料模型"""
    company_id: str  # 公司代號
    user_id: str     # 帳號
    password: str    # 密碼


class PunchClockResult(BaseModel):
    """打卡結果資料模型"""
    success: bool
    timestamp: datetime
    message: str
    punch_type: str  # "clock_in" 或 "clock_out"


class ScheduleConfig(BaseModel):
    """排程設定"""
    clock_in_time: str = "09:00"
    clock_out_time: str = "18:00"
    enabled: bool = True
    weekdays_only: bool = True


class AppConfig(BaseModel):
    """應用程式設定"""
    login: LoginCredentials
    schedule: ScheduleConfig
    debug: bool = False
    headless: bool = True


class ScreenshotInfo(BaseModel):
    """截圖資訊模型"""
    path: Path
    step_name: str
    description: str
    timestamp: datetime


class TestStep(BaseModel):
    """測試步驟記錄模型"""
    step_name: str
    description: str
    success: bool
    timestamp: datetime
    screenshot_path: Optional[Path] = None
    error_message: Optional[str] = None


class VisualTestResult(BaseModel):
    """視覺化測試結果模型"""
    test_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    overall_success: bool = False
    steps: List[TestStep] = []
    screenshots: List[ScreenshotInfo] = []
    error_screenshots: List[ScreenshotInfo] = []
    
    @property
    def duration(self) -> Optional[float]:
        """計算測試持續時間（秒）"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """計算成功率"""
        if not self.steps:
            return 0.0
        successful_steps = sum(1 for step in self.steps if step.success)
        return successful_steps / len(self.steps)