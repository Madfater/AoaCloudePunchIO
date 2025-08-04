"""
配置管理模組
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from src.models import LoginCredentials, ScheduleConfig, AppConfig, GPSConfig


class ConfigManager:
    """配置管理器 - 使用環境變數進行配置"""
    
    def __init__(self, env_file: str = ".env"):
        self.env_file = env_file
        self._config: Optional[AppConfig] = None
        
        # 載入環境變數
        if Path(env_file).exists():
            load_dotenv(env_file)
    
    def load_config(self) -> AppConfig:
        """從環境變數載入配置"""
        if self._config is not None:
            return self._config
        
        # 登入憑證 - 必要參數
        login_config = LoginCredentials(
            company_id=self._get_required_env('COMPANY_ID'),
            user_id=self._get_required_env('USER_ID'),
            password=self._get_required_env('PASSWORD')
        )
        
        # 排程設定 - 必要參數
        schedule_config = ScheduleConfig(
            clock_in_time=self._get_required_env('CLOCK_IN_TIME'),
            clock_out_time=self._get_required_env('CLOCK_OUT_TIME'),
            enabled=self._get_required_bool_env('SCHEDULE_ENABLED'),
            weekdays_only=self._get_required_bool_env('WEEKDAYS_ONLY')
        )
        
        # GPS 設定 - 必要參數
        gps_config = GPSConfig(
            latitude=self._get_required_float_env('GPS_LATITUDE'),
            longitude=self._get_required_float_env('GPS_LONGITUDE'),
            address=self._get_required_env('GPS_ADDRESS')
        )
        
        # 應用程式設定
        self._config = AppConfig(
            login=login_config,
            schedule=schedule_config,
            gps=gps_config,
            debug=self._get_required_bool_env('DEBUG'),
            headless=self._get_required_bool_env('HEADLESS')
        )
        
        return self._config
    
    def get_login_credentials(self) -> LoginCredentials:
        """取得登入憑證"""
        config = self.load_config()
        return config.login
    
    def _get_required_env(self, key: str) -> str:
        """取得必要的環境變數，不存在時拋出異常"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"必要環境變數未設定: {key}")
        return value
    
    def _get_required_bool_env(self, key: str) -> bool:
        """取得必要的布林型環境變數，不存在或格式錯誤時拋出異常"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"必要環境變數未設定: {key}")
        
        value_lower = value.lower()
        if value_lower in ('true', '1', 'yes', 'on'):
            return True
        elif value_lower in ('false', '0', 'no', 'off'):
            return False
        else:
            raise ValueError(f"環境變數 {key} 的值 '{value}' 不是有效的布林值。請使用: true/false, 1/0, yes/no, on/off")
    
    def _get_required_float_env(self, key: str) -> float:
        """取得必要的浮點數型環境變數，不存在或格式錯誤時拋出異常"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"必要環境變數未設定: {key}")
        
        try:
            return float(value)
        except ValueError:
            raise ValueError(f"環境變數 {key} 的值 '{value}' 不是有效的數字")


# 全域實例
config_manager = ConfigManager()