"""
震旦HR系統自動打卡核心模組
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from playwright.async_api import async_playwright, Browser, Page
from loguru import logger

from .models import LoginCredentials


class AoaCloudPunchClock:
    """震旦HR系統自動打卡類別"""
    
    def __init__(self, headless: bool = True, enable_screenshots: bool = False, screenshots_dir: str = "screenshots"):
        self.headless = headless
        self.enable_screenshots = enable_screenshots
        self.screenshots_dir = Path(screenshots_dir)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._base_url = "https://erpline.aoacloud.com.tw"
        self._screenshot_counter = 0
        self._screenshots_taken: List[Path] = []
        
        # 建立截圖目錄
        if self.enable_screenshots:
            self.screenshots_dir.mkdir(exist_ok=True)
            logger.info(f"截圖將保存到: {self.screenshots_dir}")
        
    async def __aenter__(self):
        """異步上下文管理器進入"""
        await self._initialize_browser()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器退出"""
        await self._cleanup()
        
    async def _initialize_browser(self) -> None:
        """初始化瀏覽器"""
        try:
            self.playwright = await async_playwright().start()
            
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security'
                ]
            )
            
            self.page = await self.browser.new_page()
            
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                             '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            logger.info("瀏覽器初始化完成")
            
        except Exception as e:
            logger.error(f"瀏覽器初始化失敗: {e}")
            raise
            
    async def _cleanup(self) -> None:
        """清理資源"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            logger.info("資源清理完成")
        except Exception as e:
            logger.error(f"資源清理失敗: {e}")
    
    async def _take_screenshot(self, step_name: str, description: str = "") -> Optional[Path]:
        """截取頁面截圖"""
        if not self.enable_screenshots or not self.page:
            return None
            
        try:
            self._screenshot_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self._screenshot_counter:02d}_{timestamp}_{step_name}.png"
            screenshot_path = self.screenshots_dir / filename
            
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            self._screenshots_taken.append(screenshot_path)
            
            log_msg = f"截圖已保存: {screenshot_path}"
            if description:
                log_msg += f" - {description}"
            logger.info(log_msg)
            
            return screenshot_path
            
        except Exception as e:
            logger.error(f"截圖失敗: {e}")
            return None
    
    async def _take_error_screenshot(self, error_context: str) -> Optional[Path]:
        """發生錯誤時截取頁面截圖"""
        return await self._take_screenshot("error", f"錯誤狀況: {error_context}")
    
    def get_screenshots_taken(self) -> List[Path]:
        """獲取已截取的截圖列表"""
        return self._screenshots_taken.copy()
            
    async def login(self, credentials: LoginCredentials) -> bool:
        """登入震旦HR系統"""
        try:
            logger.info("開始登入流程...")
            
            response = await self.page.goto(self._base_url, wait_until='networkidle')
            
            if not response or response.status != 200:
                logger.error(f"無法載入登入頁面，狀態碼: {response.status if response else 'None'}")
                await self._take_error_screenshot("頁面載入失敗")
                return False
            
            logger.info("登入頁面載入成功")
            await self._take_screenshot("page_loaded", "登入頁面載入完成")
            
            # 等待登入表單載入
            await self.page.wait_for_selector('input[name="CompId"]', timeout=10000)
            
            # 填入憑證
            await self.page.fill('input[name="CompId"]', credentials.company_id)
            await self.page.fill('input[name="UserId"]', credentials.user_id)
            await self.page.fill('input[name="Passwd"]', credentials.password)
            
            logger.info("已填入登入資訊")
            await self._take_screenshot("credentials_filled", "登入資訊填寫完成")
            
            # 點擊登入按鈕
            await self.page.click('button:has-text("登入")')
            logger.info("已點擊登入按鈕")
            
            # 等待頁面跳轉
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            
            current_url = self.page.url
            if current_url != self._base_url and "login" not in current_url.lower():
                logger.info(f"登入成功，當前URL: {current_url}")
                await self._take_screenshot("login_success", f"登入成功頁面 - {current_url}")
                return True
            else:
                logger.error("登入失敗：未能成功跳轉")
                await self._take_error_screenshot("登入失敗")
                return False
                
        except Exception as e:
            logger.error(f"登入過程中發生錯誤: {e}")
            await self._take_error_screenshot(f"登入異常: {str(e)}")
            return False