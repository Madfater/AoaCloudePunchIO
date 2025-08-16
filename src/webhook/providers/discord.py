"""
Discord Webhook Provider 實作
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from loguru import logger

from src.models.webhook import (
    WebhookMessage, WebhookResponse, WebhookConfig, 
    DiscordEmbed, DiscordWebhookPayload, NotificationLevel
)
from .base import WebhookProvider
from ..exceptions import WebhookTimeoutError, WebhookRateLimitError, WebhookAuthError


class DiscordWebhookProvider(WebhookProvider):
    """Discord Webhook Provider"""
    
    def __init__(self, config: WebhookConfig):
        super().__init__(config)
        self.webhook_url = str(config.discord_url) if config.discord_url else None
    
    @property
    def provider_name(self) -> str:
        return "Discord"
    
    def validate_config(self) -> bool:
        """驗證 Discord 配置"""
        if not self.webhook_url:
            logger.error("Discord webhook URL 未設定")
            return False
        
        if not self.webhook_url.startswith("https://discord.com/api/webhooks/"):
            logger.error("Discord webhook URL 格式不正確")
            return False
        
        return True
    
    async def send_message(self, message: WebhookMessage) -> WebhookResponse:
        """發送訊息到 Discord Webhook"""
        if not self.validate_config():
            return WebhookResponse(
                success=False,
                provider=self.provider_name,
                error_message="Discord 配置無效"
            )
        
        if not self.should_notify(message):
            logger.debug(f"根據配置跳過 Discord 通知: {message.level}")
            return WebhookResponse(
                success=True,
                provider=self.provider_name,
                status_code=200,
                response_text="通知已跳過（根據配置）"
            )
        
        try:
            # 建立 Discord payload
            payload = self._create_discord_payload(message)
            
            # 準備附件
            files = None
            if message.attachments:
                valid_attachments = self._format_attachments(message.attachments)
                if valid_attachments:
                    files = await self._prepare_files(valid_attachments)
            
            # 發送請求
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)) as session:
                if files:
                    # 有附件時使用 multipart/form-data
                    data = aiohttp.FormData()
                    data.add_field('payload_json', json.dumps(payload.model_dump(exclude_none=True)))
                    
                    for i, file_path in enumerate(files):
                        file_obj = open(file_path, 'rb')
                        data.add_field(f'file{i}', file_obj, filename=Path(file_path).name)
                    
                    async with session.post(self.webhook_url, data=data) as response:
                        # 關閉檔案
                        for field in data._fields:
                            if hasattr(field[2], 'close'):
                                field[2].close()
                        
                        return await self._handle_response(response)
                else:
                    # 純文字訊息
                    async with session.post(
                        self.webhook_url,
                        json=payload.model_dump(exclude_none=True),
                        headers={'Content-Type': 'application/json'}
                    ) as response:
                        return await self._handle_response(response)
                        
        except asyncio.TimeoutError:
            raise WebhookTimeoutError(f"Discord webhook 請求超時 ({self.config.timeout_seconds}秒)")
        except Exception as e:
            logger.error(f"Discord webhook 發送失敗: {e}")
            return WebhookResponse(
                success=False,
                provider=self.provider_name,
                error_message=str(e)
            )
    
    def _create_discord_payload(self, message: WebhookMessage) -> DiscordWebhookPayload:
        """建立 Discord webhook payload"""
        # 建立 embed
        embed = DiscordEmbed(
            title=message.title,
            description=message.message,
            color=message.color_code,
            timestamp=message.timestamp.isoformat()
        )
        
        # 添加欄位
        if message.details:
            embed.fields = []
            for key, value in message.details.items():
                if value is not None:
                    embed.fields.append({
                        "name": str(key),
                        "value": str(value),
                        "inline": True
                    })
        
        # 添加頁尾
        embed.footer = {
            "text": f"震旦HR打卡系統 • {message.level.value.upper()}"
        }
        
        # 建立 payload
        return DiscordWebhookPayload(
            embeds=[embed],
            username="震旦HR打卡機器人"
        )
    
    async def _prepare_files(self, file_paths: List[str]) -> List[str]:
        """準備要上傳的檔案"""
        valid_files = []
        
        for file_path in file_paths:
            try:
                path = Path(file_path)
                if path.exists() and path.stat().st_size <= 8 * 1024 * 1024:  # Discord 8MB 限制
                    valid_files.append(str(path))
                else:
                    logger.warning(f"檔案過大或不存在，跳過上傳: {file_path}")
            except Exception as e:
                logger.error(f"處理檔案時發生錯誤 {file_path}: {e}")
        
        return valid_files
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> WebhookResponse:
        """處理 Discord API 回應"""
        response_text = await response.text()
        
        if response.status == 200 or response.status == 204:
            logger.debug("Discord webhook 發送成功")
            return WebhookResponse(
                success=True,
                provider=self.provider_name,
                status_code=response.status,
                response_text=response_text
            )
        elif response.status == 429:
            # 速率限制
            retry_after = response.headers.get('Retry-After', '1')
            raise WebhookRateLimitError(f"Discord API 速率限制，請等待 {retry_after} 秒")
        elif response.status == 401 or response.status == 403:
            raise WebhookAuthError(f"Discord webhook 認證失敗: {response_text}")
        else:
            logger.error(f"Discord webhook 發送失敗: {response.status} - {response_text}")
            return WebhookResponse(
                success=False,
                provider=self.provider_name,
                status_code=response.status,
                response_text=response_text,
                error_message=f"HTTP {response.status}: {response_text}"
            )
    
    def create_punch_notification(self, action: str, success: bool, 
                                 result_message: str, details: Optional[Dict[str, Any]] = None,
                                 screenshots: Optional[List[str]] = None) -> WebhookMessage:
        """建立打卡通知訊息
        
        Args:
            action: 打卡動作 ("簽到" 或 "簽退")
            success: 是否成功
            result_message: 結果訊息
            details: 額外詳細資訊
            screenshots: 截圖檔案路徑列表
            
        Returns:
            WebhookMessage: 格式化的通知訊息
        """
        if success:
            title = f"🎉 {action}成功"
            level = NotificationLevel.SUCCESS
            message = f"✅ {result_message}"
        else:
            title = f"❌ {action}失敗"
            level = NotificationLevel.ERROR
            message = f"💥 {result_message}"
        
        # 準備詳細資訊
        notification_details = {
            "動作": action,
            "時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        if details:
            notification_details.update(details)
        
        return WebhookMessage(
            title=title,
            message=message,
            level=level,
            action=action,
            result=result_message,
            details=notification_details,
            attachments=screenshots
        )
    
    def create_scheduler_notification(self, event: str, message: str, 
                                    details: Optional[Dict[str, Any]] = None) -> WebhookMessage:
        """建立排程器通知訊息
        
        Args:
            event: 事件類型 ("啟動", "停止", "錯誤" 等)
            message: 訊息內容
            details: 額外詳細資訊
            
        Returns:
            WebhookMessage: 格式化的通知訊息
        """
        title_map = {
            "啟動": "🕐 排程器啟動",
            "停止": "💤 排程器停止", 
            "錯誤": "🚨 排程器錯誤"
        }
        
        level_map = {
            "啟動": NotificationLevel.INFO,
            "停止": NotificationLevel.INFO,
            "錯誤": NotificationLevel.ERROR
        }
        
        return WebhookMessage(
            title=title_map.get(event, f"📋 排程器{event}"),
            message=message,
            level=level_map.get(event, NotificationLevel.INFO),
            details=details or {"事件": event, "時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        )