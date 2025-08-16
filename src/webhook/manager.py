"""
Webhook Manager - 統一的 webhook 管理器
"""

import asyncio
from typing import List, Optional, Dict, Any
from loguru import logger

from src.models.webhook import WebhookConfig, WebhookMessage, WebhookResponse
from .providers import WebhookProvider, DiscordWebhookProvider


class WebhookManager:
    """Webhook 管理器 - 統一管理所有 webhook 提供者"""
    
    def __init__(self, config: WebhookConfig):
        self.config = config
        self.providers: List[WebhookProvider] = []
        self._initialize_providers()
    
    def _initialize_providers(self):
        """初始化 webhook 提供者"""
        self.providers.clear()
        
        if not self.config.enabled:
            logger.debug("Webhook 功能已停用")
            return
        
        # 初始化 Discord provider
        if self.config.discord_url:
            try:
                discord_provider = DiscordWebhookProvider(self.config)
                if discord_provider.validate_config():
                    self.providers.append(discord_provider)
                    logger.info("Discord webhook provider 已初始化")
                else:
                    logger.warning("Discord webhook 配置無效，跳過初始化")
            except Exception as e:
                logger.error(f"初始化 Discord webhook provider 失敗: {e}")
        
        # 未來可以在這裡添加其他 providers (Slack, Teams 等)
        
        if not self.providers:
            logger.warning("沒有可用的 webhook 提供者")
    
    async def send_notification(self, message: WebhookMessage) -> List[WebhookResponse]:
        """發送通知到所有已配置的 webhook
        
        Args:
            message: 要發送的訊息
            
        Returns:
            List[WebhookResponse]: 所有 provider 的回應結果
        """
        if not self.providers:
            logger.debug("沒有可用的 webhook 提供者，跳過通知發送")
            return []
        
        logger.info(f"發送 webhook 通知: {message.title} ({message.level.value})")
        
        # 並行發送到所有 providers
        tasks = []
        for provider in self.providers:
            if provider.should_notify(message):
                task = asyncio.create_task(
                    provider.send_with_retry(message),
                    name=f"webhook_{provider.provider_name}"
                )
                tasks.append(task)
            else:
                logger.debug(f"根據配置跳過 {provider.provider_name} 通知")
        
        if not tasks:
            logger.debug("所有 webhook 通知都被配置跳過")
            return []
        
        # 等待所有任務完成
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 處理結果
        webhook_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error(f"Webhook 發送任務異常: {response}")
                webhook_responses.append(WebhookResponse(
                    success=False,
                    provider=f"provider_{i}",
                    error_message=str(response)
                ))
            else:
                webhook_responses.append(response)
        
        # 統計結果
        successful = sum(1 for r in webhook_responses if r.success)
        total = len(webhook_responses)
        
        if successful == total:
            logger.info(f"所有 webhook 通知發送成功 ({successful}/{total})")
        elif successful > 0:
            logger.warning(f"部分 webhook 通知發送成功 ({successful}/{total})")
        else:
            logger.error(f"所有 webhook 通知發送失敗 ({successful}/{total})")
        
        return webhook_responses
    
    async def send_punch_notification(self, action: str, success: bool, 
                                    result_message: str, details: Optional[Dict[str, Any]] = None,
                                    screenshots: Optional[List[str]] = None) -> List[WebhookResponse]:
        """發送打卡通知
        
        Args:
            action: 打卡動作 ("簽到" 或 "簽退")
            success: 是否成功
            result_message: 結果訊息
            details: 額外詳細資訊
            screenshots: 截圖檔案路徑列表
            
        Returns:
            List[WebhookResponse]: 發送結果
        """
        # 使用 Discord provider 建立通知訊息（其他 provider 可以有各自的格式）
        discord_providers = [p for p in self.providers if isinstance(p, DiscordWebhookProvider)]
        
        if discord_providers:
            message = discord_providers[0].create_punch_notification(
                action, success, result_message, details, screenshots
            )
            return await self.send_notification(message)
        else:
            # 如果沒有 Discord provider，建立通用訊息
            from src.models.webhook import NotificationLevel
            
            level = NotificationLevel.SUCCESS if success else NotificationLevel.ERROR
            title = f"{'🎉' if success else '❌'} {action}{'成功' if success else '失敗'}"
            
            message = WebhookMessage(
                title=title,
                message=result_message,
                level=level,
                action=action,
                result=result_message,
                details=details,
                attachments=screenshots
            )
            return await self.send_notification(message)
    
    async def send_scheduler_notification(self, event: str, message_text: str, 
                                        details: Optional[Dict[str, Any]] = None) -> List[WebhookResponse]:
        """發送排程器通知
        
        Args:
            event: 事件類型 ("啟動", "停止", "錯誤" 等)
            message_text: 訊息內容
            details: 額外詳細資訊
            
        Returns:
            List[WebhookResponse]: 發送結果
        """
        # 使用 Discord provider 建立通知訊息
        discord_providers = [p for p in self.providers if isinstance(p, DiscordWebhookProvider)]
        
        if discord_providers:
            message = discord_providers[0].create_scheduler_notification(
                event, message_text, details
            )
            return await self.send_notification(message)
        else:
            # 如果沒有 Discord provider，建立通用訊息
            from src.models.webhook import NotificationLevel
            
            level_map = {
                "啟動": NotificationLevel.INFO,
                "停止": NotificationLevel.INFO,
                "錯誤": NotificationLevel.ERROR
            }
            
            message = WebhookMessage(
                title=f"📋 排程器{event}",
                message=message_text,
                level=level_map.get(event, NotificationLevel.INFO),
                details=details
            )
            return await self.send_notification(message)
    
    async def test_webhooks(self) -> List[WebhookResponse]:
        """測試所有 webhook 連線
        
        Returns:
            List[WebhookResponse]: 測試結果
        """
        test_message = WebhookMessage(
            title="🧪 Webhook 連線測試",
            message="這是一條測試訊息，用於驗證 webhook 配置是否正確。",
            level="info"
        )
        
        logger.info("開始測試 webhook 連線...")
        responses = await self.send_notification(test_message)
        
        for response in responses:
            if response.success:
                logger.info(f"✅ {response.provider} webhook 測試成功")
            else:
                logger.error(f"❌ {response.provider} webhook 測試失敗: {response.error_message}")
        
        return responses
    
    def reload_config(self, new_config: WebhookConfig):
        """重新載入配置
        
        Args:
            new_config: 新的 webhook 配置
        """
        logger.info("重新載入 webhook 配置...")
        self.config = new_config
        self._initialize_providers()
        logger.info(f"Webhook 配置已更新，當前有 {len(self.providers)} 個可用的提供者")
    
    @property
    def is_enabled(self) -> bool:
        """檢查 webhook 是否已啟用"""
        return self.config.enabled and len(self.providers) > 0
    
    @property
    def available_providers(self) -> List[str]:
        """取得可用的 provider 名稱列表"""
        return [provider.provider_name for provider in self.providers]