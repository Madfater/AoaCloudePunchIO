"""
震旦HR系統自動打卡核心模組
"""

import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page
from loguru import logger

from models import LoginCredentials, PunchClockResult


class AoaCloudPunchClock:
    """震旦HR系統自動打卡類別"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._base_url = "https://erpline.aoacloud.com.tw"
        
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
            
    async def login(self, credentials: LoginCredentials) -> bool:
        """登入震旦HR系統"""
        try:
            logger.info("開始登入流程...")
            
            response = await self.page.goto(self._base_url, wait_until='networkidle')
            
            if not response or response.status != 200:
                logger.error(f"無法載入登入頁面，狀態碼: {response.status if response else 'None'}")
                return False
            
            logger.info("登入頁面載入成功")
            
            # 等待登入表單載入
            await self.page.wait_for_selector('input[name="CompId"]', timeout=10000)
            
            # 填入憑證
            await self.page.fill('input[name="CompId"]', credentials.company_id)
            await self.page.fill('input[name="UserId"]', credentials.user_id)
            await self.page.fill('input[name="Passwd"]', credentials.password)
            
            logger.info("已填入登入資訊")
            
            # 點擊登入按鈕
            await self.page.click('button:has-text("登入")')
            logger.info("已點擊登入按鈕")
            
            # 等待頁面跳轉
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            
            current_url = self.page.url
            if current_url != self._base_url and "login" not in current_url.lower():
                logger.info(f"登入成功，當前URL: {current_url}")
                return True
            else:
                logger.error("登入失敗：未能成功跳轉")
                return False
                
        except Exception as e:
            logger.error(f"登入過程中發生錯誤: {e}")
            return False