"""
截圖管理模組
負責處理截圖功能和檔案管理
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
from playwright.async_api import Page
from loguru import logger


class ScreenshotManager:
    """截圖管理器"""
    
    def __init__(self, page: Page, enable_screenshots: bool = False, screenshots_dir: str = "screenshots"):
        self.page = page
        self.enable_screenshots = enable_screenshots
        self.screenshots_dir = Path(screenshots_dir)
        self._screenshot_counter = 0
        self._screenshots_taken: List[Path] = []
        
        # 建立截圖目錄
        if self.enable_screenshots:
            self.screenshots_dir.mkdir(exist_ok=True)
            logger.info(f"截圖將保存到: {self.screenshots_dir}")
    
    async def take_screenshot(self, step_name: str, description: str = "") -> Optional[Path]:
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
    
    async def take_error_screenshot(self, error_context: str) -> Optional[Path]:
        """發生錯誤時截取頁面截圖"""
        return await self.take_screenshot("error", f"錯誤狀況: {error_context}")
    
    def get_screenshots_taken(self) -> List[Path]:
        """獲取已截取的截圖列表"""
        return self._screenshots_taken.copy()
    
    def get_screenshot_count(self) -> int:
        """獲取截圖數量"""
        return len(self._screenshots_taken)
    
    def is_enabled(self) -> bool:
        """檢查截圖功能是否啟用"""
        return self.enable_screenshots
    
    def clear_screenshots(self) -> None:
        """清空截圖記錄（不刪除檔案）"""
        self._screenshots_taken.clear()
        self._screenshot_counter = 0
        logger.info("截圖記錄已清空")
    
    def delete_screenshots(self) -> int:
        """刪除所有截圖檔案"""
        deleted_count = 0
        for screenshot_path in self._screenshots_taken:
            try:
                if screenshot_path.exists():
                    screenshot_path.unlink()
                    deleted_count += 1
            except Exception as e:
                logger.error(f"刪除截圖失敗 {screenshot_path}: {e}")
        
        if deleted_count > 0:
            logger.info(f"已刪除 {deleted_count} 個截圖檔案")
        
        self.clear_screenshots()
        return deleted_count
    
    def get_screenshots_info(self) -> List[dict]:
        """獲取截圖資訊列表"""
        screenshots_info = []
        for screenshot_path in self._screenshots_taken:
            try:
                stat = screenshot_path.stat()
                screenshots_info.append({
                    "path": screenshot_path,
                    "name": screenshot_path.name,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime),
                    "exists": screenshot_path.exists()
                })
            except Exception as e:
                screenshots_info.append({
                    "path": screenshot_path,
                    "name": screenshot_path.name,
                    "size": 0,
                    "created": None,
                    "exists": False,
                    "error": str(e)
                })
        return screenshots_info