"""
配置管理模組
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from src.models import LoginCredentials, ScheduleConfig, AppConfig, GPSConfig, WebhookConfig


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
            weekdays_only=self._get_required_bool_env('WEEKDAYS_ONLY'),
            status_message_interval=self._get_optional_int_env('STATUS_MESSAGE_INTERVAL', 300)
        )
        
        # GPS 設定 - 必要參數
        gps_config = GPSConfig(
            latitude=self._get_required_float_env('GPS_LATITUDE'),
            longitude=self._get_required_float_env('GPS_LONGITUDE'),
            address=self._get_required_env('GPS_ADDRESS')
        )
        
        # Webhook 設定 - 可選參數
        webhook_config = WebhookConfig(
            enabled=self._get_optional_bool_env('WEBHOOK_ENABLED', False),
            discord_url=self._get_optional_env('DISCORD_WEBHOOK_URL'),
            slack_url=self._get_optional_env('SLACK_WEBHOOK_URL'),
            teams_url=self._get_optional_env('TEAMS_WEBHOOK_URL'),
            notify_success=self._get_optional_bool_env('WEBHOOK_NOTIFY_SUCCESS', True),
            notify_failure=self._get_optional_bool_env('WEBHOOK_NOTIFY_FAILURE', True),
            notify_scheduler=self._get_optional_bool_env('WEBHOOK_NOTIFY_SCHEDULER', True),
            notify_errors=self._get_optional_bool_env('WEBHOOK_NOTIFY_ERRORS', True),
            timeout_seconds=self._get_optional_int_env('WEBHOOK_TIMEOUT_SECONDS', 30),
            retry_attempts=self._get_optional_int_env('WEBHOOK_RETRY_ATTEMPTS', 3),
            rate_limit_delay=self._get_optional_float_env('WEBHOOK_RATE_LIMIT_DELAY', 1.0)
        )
        
        # 應用程式設定
        self._config = AppConfig(
            login=login_config,
            schedule=schedule_config,
            gps=gps_config,
            webhook=webhook_config,
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
    
    def _get_optional_int_env(self, key: str, default: int) -> int:
        """取得可選的整數型環境變數，不存在時返回預設值"""
        value = os.getenv(key)
        if not value:
            return default
        
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"環境變數 {key} 的值 '{value}' 不是有效的整數")
    
    def _get_optional_env(self, key: str, default: str = None) -> Optional[str]:
        """取得可選的環境變數，不存在時返回預設值"""
        value = os.getenv(key, default)
        return value if value else None
    
    def _get_optional_bool_env(self, key: str, default: bool) -> bool:
        """取得可選的布林型環境變數，不存在時返回預設值"""
        value = os.getenv(key)
        if not value:
            return default
        
        value_lower = value.lower()
        if value_lower in ('true', '1', 'yes', 'on'):
            return True
        elif value_lower in ('false', '0', 'no', 'off'):
            return False
        else:
            raise ValueError(f"環境變數 {key} 的值 '{value}' 不是有效的布林值。請使用: true/false, 1/0, yes/no, on/off")
    
    def _get_optional_float_env(self, key: str, default: float) -> float:
        """取得可選的浮點數型環境變數，不存在時返回預設值"""
        value = os.getenv(key)
        if not value:
            return default
        
        try:
            return float(value)
        except ValueError:
            raise ValueError(f"環境變數 {key} 的值 '{value}' 不是有效的數字")


# 全域實例
config_manager = ConfigManager()