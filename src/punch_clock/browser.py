"""
瀏覽器管理模組
負責瀏覽器的初始化、配置和清理
"""

from typing import Optional, Literal
from playwright.async_api import async_playwright, Browser, Page, Playwright
from loguru import logger

from src.models import GPSConfig
from src.retry_handler import BrowserError


class BrowserManager:
    """瀏覽器生命周期管理器"""
    
    def __init__(self, headless: bool = True, gps_config: Optional[GPSConfig] = None):
        self.headless = headless
        self.gps_config = gps_config or GPSConfig()
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._base_url = "https://erpline.aoacloud.com.tw"
    
    async def initialize(self) -> Page:
        """初始化瀏覽器並返回頁面實例"""
        try:
            self.playwright = await async_playwright().start()
            
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--use-fake-ui-for-media-stream',
                    '--use-fake-device-for-media-stream'
                ]
            )
            
            # 創建新的context以便設置權限
            context = await self.browser.new_context(
                permissions=['geolocation'],
                geolocation={
                    'latitude': self.gps_config.latitude, 
                    'longitude': self.gps_config.longitude
                }
            )
            
            self.page = await context.new_page()
            
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                             '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            # 監聽並自動處理權限對話框
            self.page.on('dialog', self._handle_dialog)
            
            logger.info("瀏覽器初始化完成")
            return self.page
            
        except Exception as e:
            logger.error(f"瀏覽器初始化失敗: {e}")
            await self.cleanup()
            raise BrowserError(f"瀏覽器初始化失敗: {e}")
    
    async def _handle_dialog(self, dialog):
        """處理瀏覽器對話框（如權限請求）"""
        try:
            dialog_type = dialog.type
            message = dialog.message
            
            logger.info(f"檢測到對話框 - 類型: {dialog_type}, 訊息: {message}")
            
            # 自動接受所有對話框（包括權限請求）
            await dialog.accept()
            logger.info("已自動接受對話框")
            
        except Exception as e:
            logger.error(f"處理對話框時發生錯誤: {e}")
            try:
                await dialog.dismiss()
            except Exception:
                pass
    
    async def navigate_to_base_url(self) -> bool:
        """導航到基礎URL"""
        if not self.page:
            raise BrowserError("頁面未初始化")
        
        try:
            response = await self.page.goto(self._base_url, wait_until='networkidle')
            
            if not response or response.status != 200:
                error_msg = f"無法載入頁面，狀態碼: {response.status if response else 'None'}"
                logger.error(error_msg)
                return False
            
            logger.info("基礎頁面載入成功")
            return True
            
        except Exception as e:
            logger.error(f"導航到基礎URL失敗: {e}")
            return False
    
    async def wait_for_load_state(self, state: Literal['domcontentloaded', 'load', 'networkidle'] = 'networkidle', timeout: int = 15000):
        """等待頁面載入狀態"""
        if not self.page:
            raise BrowserError("頁面未初始化")
        
        try:
            await self.page.wait_for_load_state(state, timeout=timeout)
            return True
        except Exception as e:
            logger.warning(f"等待載入狀態 {state} 超時: {e}")
            return False
    
    async def cleanup(self) -> None:
        """清理瀏覽器資源"""
        try:
            if self.page:
                await self.page.close()
                self.page = None
            if self.browser:
                await self.browser.close()
                self.browser = None
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            logger.info("瀏覽器資源清理完成")
        except Exception as e:
            logger.error(f"瀏覽器資源清理失敗: {e}")
    
    def get_page(self) -> Page:
        """獲取當前頁面實例"""
        if not self.page:
            raise BrowserError("頁面未初始化")
        return self.page
    
    def is_initialized(self) -> bool:
        """檢查瀏覽器是否已初始化"""
        return self.page is not None
    
    async def __aenter__(self):
        """異步上下文管理器進入"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器退出"""
        await self.cleanup()