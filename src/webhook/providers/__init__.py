"""
Webhook Providers 模組
"""

from .base import WebhookProvider
from .discord import DiscordWebhookProvider

__all__ = [
    "WebhookProvider",
    "DiscordWebhookProvider",
]