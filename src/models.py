"""
資料模型統一定義模組
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel


class PunchAction(str, Enum):
    """打卡動作類型枚舉"""
    SIGN_IN = "sign_in"      # 簽到
    SIGN_OUT = "sign_out"    # 簽退
    SIMULATE = "simulate"    # 模擬模式


class LoginCredentials(BaseModel):
    """登入憑證資料模型"""
    company_id: str  # 公司代號
    user_id: str     # 帳號
    password: str    # 密碼


class PunchResult(BaseModel):
    """打卡操作結果資料模型"""
    success: bool                      # 是否成功
    action: PunchAction               # 執行的動作類型
    timestamp: datetime               # 操作時間戳
    message: str                      # 結果訊息
    server_response: Optional[str] = None  # 伺服器回應訊息
    screenshot_path: Optional[Path] = None # 結果截圖路徑
    is_simulation: bool = False       # 是否為模擬模式
    
    
class PunchClockResult(BaseModel):
    """打卡結果資料模型（保持向後兼容）"""
    success: bool
    timestamp: datetime
    message: str
    punch_type: str  # "clock_in" 或 "clock_out"


class GPSConfig(BaseModel):
    """GPS 定位設定"""
    latitude: float = 25.0330  # 緯度（預設：台北市內湖路一段604號）
    longitude: float = 121.5654 # 經度
    address: str = "台北市"  # 地址描述


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
    gps: GPSConfig = GPSConfig()  # GPS 設定，使用預設值
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