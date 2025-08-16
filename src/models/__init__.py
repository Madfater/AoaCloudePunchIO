"""
Models 模組統一導出接口
保持向後兼容性，允許從 src.models 直接導入所有模型
"""

# 從 core 模組導入核心打卡相關模型
from .core import (
    PunchAction,
    LoginCredentials,
    PunchResult,
    PunchClockResult,
)

# 從 config 模組導入配置相關模型
from .config import (
    GPSConfig,
    ScheduleConfig,
    AppConfig,
)

# 從 testing 模組導入測試相關模型
from .testing import (
    ScreenshotInfo,
    TestStep,
    VisualTestResult,
)

# 從 webhook 模組導入 webhook 相關模型
from .webhook import (
    WebhookType,
    NotificationLevel,
    WebhookConfig,
    WebhookMessage,
    WebhookResponse,
    DiscordEmbed,
    DiscordWebhookPayload,
)

# 定義可公開導出的所有模型
__all__ = [
    # 核心模型
    "PunchAction",
    "LoginCredentials", 
    "PunchResult",
    "PunchClockResult",
    # 配置模型
    "GPSConfig",
    "ScheduleConfig", 
    "AppConfig",
    # 測試模型
    "ScreenshotInfo",
    "TestStep",
    "VisualTestResult",
    # Webhook 模型
    "WebhookType",
    "NotificationLevel", 
    "WebhookConfig",
    "WebhookMessage",
    "WebhookResponse",
    "DiscordEmbed",
    "DiscordWebhookPayload",
]