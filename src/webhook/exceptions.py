"""
Webhook 異常處理
"""


class WebhookError(Exception):
    """Webhook 基礎異常"""
    pass


class WebhookConfigError(WebhookError):
    """Webhook 配置錯誤"""
    pass


class WebhookTimeoutError(WebhookError):
    """Webhook 請求超時"""
    pass


class WebhookRateLimitError(WebhookError):
    """Webhook 速率限制錯誤"""
    pass


class WebhookAuthError(WebhookError):
    """Webhook 認證錯誤"""
    pass