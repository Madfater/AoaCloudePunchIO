"""
核心打卡相關資料模型
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum
from pydantic import BaseModel


class PunchAction(str, Enum):
    """打卡動作類型枚舉"""
    SIGN_IN = "sign_in"      # 簽到
    SIGN_OUT = "sign_out"    # 簽退
    SIMULATE = "simulate"    # 模擬模式


class LoginCredentials(BaseModel):
    """登入憑證資料模型"""
    company_id: str  # 公司代號
    user_id: str     # 帳號
    password: str    # 密碼


class PunchResult(BaseModel):
    """打卡操作結果資料模型"""
    success: bool                      # 是否成功
    action: PunchAction               # 執行的動作類型
    timestamp: datetime               # 操作時間戳
    message: str                      # 結果訊息
    server_response: Optional[str] = None  # 伺服器回應訊息
    screenshot_path: Optional[Path] = None # 結果截圖路徑
    is_simulation: bool = False       # 是否為模擬模式
    
    
class PunchClockResult(BaseModel):
    """打卡結果資料模型（保持向後兼容）"""
    success: bool
    timestamp: datetime
    message: str
    punch_type: str  # "clock_in" 或 "clock_out"