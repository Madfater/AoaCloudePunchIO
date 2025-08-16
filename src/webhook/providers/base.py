"""
Webhook Provider 抽象基類
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional, List
from loguru import logger

from src.models.webhook import WebhookMessage, WebhookResponse, WebhookConfig
from ..exceptions import WebhookTimeoutError, WebhookRateLimitError


class WebhookProvider(ABC):
    """Webhook Provider 抽象基類"""
    
    def __init__(self, config: WebhookConfig):
        self.config = config
        self.last_request_time = 0.0
    
    @abstractmethod
    async def send_message(self, message: WebhookMessage) -> WebhookResponse:
        """發送訊息到 webhook
        
        Args:
            message: 要發送的訊息
            
        Returns:
            WebhookResponse: 發送結果
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """驗證配置是否有效
        
        Returns:
            bool: 配置是否有效
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider 名稱"""
        pass
    
    async def send_with_retry(self, message: WebhookMessage) -> WebhookResponse:
        """帶重試機制的發送訊息
        
        Args:
            message: 要發送的訊息
            
        Returns:
            WebhookResponse: 發送結果
        """
        last_exception = None
        
        for attempt in range(1, self.config.retry_attempts + 1):
            try:
                # 速率限制
                await self._rate_limit()
                
                # 嘗試發送
                response = await self.send_message(message)
                
                if response.success:
                    if attempt > 1:
                        logger.info(f"Webhook 重試成功 ({self.provider_name}, 第{attempt}次嘗試)")
                    return response
                else:
                    logger.warning(f"Webhook 發送失敗 ({self.provider_name}, 第{attempt}次嘗試): {response.error_message}")
                    
            except WebhookTimeoutError as e:
                last_exception = e
                logger.warning(f"Webhook 請求超時 ({self.provider_name}, 第{attempt}次嘗試): {e}")
                
            except WebhookRateLimitError as e:
                last_exception = e
                logger.warning(f"Webhook 速率限制 ({self.provider_name}, 第{attempt}次嘗試): {e}")
                # 速率限制錯誤等待更長時間
                await asyncio.sleep(min(5.0 * attempt, 30.0))
                
            except Exception as e:
                last_exception = e
                logger.error(f"Webhook 發送異常 ({self.provider_name}, 第{attempt}次嘗試): {e}")
            
            # 等待後重試
            if attempt < self.config.retry_attempts:
                wait_time = min(2.0 ** attempt, 10.0)  # 指數退避，最大10秒
                logger.debug(f"等待 {wait_time} 秒後重試...")
                await asyncio.sleep(wait_time)
        
        # 所有重試都失敗
        error_msg = f"Webhook 發送失敗，已重試 {self.config.retry_attempts} 次"
        if last_exception:
            error_msg += f": {last_exception}"
        
        logger.error(error_msg)
        return WebhookResponse(
            success=False,
            provider=self.provider_name,
            error_message=error_msg
        )
    
    async def _rate_limit(self):
        """速率限制控制"""
        import time
        
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.config.rate_limit_delay:
            wait_time = self.config.rate_limit_delay - time_since_last
            logger.debug(f"速率限制等待 {wait_time:.2f} 秒")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def should_notify(self, message: WebhookMessage) -> bool:
        """檢查是否應該發送通知
        
        Args:
            message: 訊息
            
        Returns:
            bool: 是否應該發送
        """
        from src.models.webhook import NotificationLevel
        
        if not self.config.enabled:
            return False
        
        # 根據通知等級和配置決定是否發送
        level_config_map = {
            NotificationLevel.SUCCESS: self.config.notify_success,
            NotificationLevel.ERROR: self.config.notify_failure,
            NotificationLevel.WARNING: self.config.notify_errors,
            NotificationLevel.INFO: self.config.notify_scheduler,
        }
        
        return level_config_map.get(message.level, True)
    
    def _format_attachments(self, attachments: Optional[List[str]]) -> List[str]:
        """格式化附件列表
        
        Args:
            attachments: 原始附件路徑列表
            
        Returns:
            List[str]: 有效的附件路徑列表
        """
        if not attachments:
            return []
        
        valid_attachments = []
        for path in attachments:
            try:
                from pathlib import Path
                file_path = Path(path)
                if file_path.exists() and file_path.is_file():
                    valid_attachments.append(str(file_path.absolute()))
                else:
                    logger.warning(f"附件檔案不存在: {path}")
            except Exception as e:
                logger.error(f"處理附件時發生錯誤 {path}: {e}")
        
        return valid_attachments