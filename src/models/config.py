"""
配置相關資料模型
"""

from pydantic import BaseModel
from .core import LoginCredentials


class GPSConfig(BaseModel):
    """GPS 定位設定"""
    latitude: float = 25  # 緯度
    longitude: float = 121 # 經度
    address: str = "台北市"  # 地址描述


class ScheduleConfig(BaseModel):
    """排程設定"""
    clock_in_time: str = "09:00"
    clock_out_time: str = "18:00"
    enabled: bool = True
    weekdays_only: bool = True
    status_message_interval: int = 300  # 定期確認訊息間隔時間（秒），預設5分鐘


class AppConfig(BaseModel):
    """應用程式設定"""
    login: LoginCredentials
    schedule: ScheduleConfig
    gps: GPSConfig = GPSConfig()  # GPS 設定，使用預設值
    debug: bool = False
    headless: bool = True