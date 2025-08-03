"""
資料模型統一定義模組
"""

from datetime import datetime
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