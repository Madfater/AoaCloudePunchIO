"""
測試相關資料模型
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel


class ScreenshotInfo(BaseModel):
    """截圖資訊模型"""
    path: Path
    step_name: str
    description: str
    timestamp: datetime


class TestStep(BaseModel):
    """測試步驟記錄模型"""
    step_name: str
    description: str
    success: bool
    timestamp: datetime
    screenshot_path: Optional[Path] = None
    error_message: Optional[str] = None


class VisualTestResult(BaseModel):
    """視覺化測試結果模型"""
    test_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    overall_success: bool = False
    steps: List[TestStep] = []
    screenshots: List[ScreenshotInfo] = []
    error_screenshots: List[ScreenshotInfo] = []
    
    @property
    def duration(self) -> Optional[float]:
        """計算測試持續時間（秒）"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """計算成功率"""
        if not self.steps:
            return 0.0
        successful_steps = sum(1 for step in self.steps if step.success)
        return successful_steps / len(self.steps)