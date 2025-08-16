"""
Webhook 相關資料模型
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, HttpUrl, Field


class WebhookType(str, Enum):
    """Webhook 類型"""
    DISCORD = "discord"
    SLACK = "slack"
    TEAMS = "teams"
    GENERIC = "generic"


class NotificationLevel(str, Enum):
    """通知等級"""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


class WebhookConfig(BaseModel):
    """Webhook 配置"""
    enabled: bool = False
    discord_url: Optional[HttpUrl] = None
    slack_url: Optional[HttpUrl] = None
    teams_url: Optional[HttpUrl] = None
    
    # 通知設定
    notify_success: bool = True
    notify_failure: bool = True
    notify_scheduler: bool = True
    notify_errors: bool = True
    
    # 進階設定
    timeout_seconds: int = 30
    retry_attempts: int = 3
    rate_limit_delay: float = 1.0


class WebhookMessage(BaseModel):
    """統一的 Webhook 訊息格式"""
    title: str
    message: str
    level: NotificationLevel
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # 額外資訊
    action: Optional[str] = None
    result: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    # 附件
    attachments: Optional[List[str]] = None  # 檔案路徑列表
    
    # 顏色編碼（用於 Discord embeds）
    @property
    def color_code(self) -> int:
        """根據通知等級返回顏色代碼"""
        color_map = {
            NotificationLevel.SUCCESS: 0x00ff00,  # 綠色
            NotificationLevel.WARNING: 0xffaa00,  # 橘色
            NotificationLevel.ERROR: 0xff0000,    # 紅色
            NotificationLevel.INFO: 0x0099ff      # 藍色
        }
        return color_map.get(self.level, 0x808080)  # 預設灰色


class WebhookResponse(BaseModel):
    """Webhook 回應結果"""
    success: bool
    provider: str
    status_code: Optional[int] = None
    response_text: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class DiscordEmbed(BaseModel):
    """Discord Embed 格式"""
    title: str
    description: str
    color: int
    timestamp: str
    
    # 欄位
    fields: Optional[List[Dict[str, Any]]] = None
    
    # 頁尾
    footer: Optional[Dict[str, str]] = None
    
    # 縮圖
    thumbnail: Optional[Dict[str, str]] = None


class DiscordWebhookPayload(BaseModel):
    """Discord Webhook 請求格式"""
    content: Optional[str] = None
    embeds: Optional[List[DiscordEmbed]] = None
    username: Optional[str] = "震旦HR打卡機器人"
    avatar_url: Optional[str] = None
    
    # 檔案上傳時使用
    files: Optional[List[str]] = None