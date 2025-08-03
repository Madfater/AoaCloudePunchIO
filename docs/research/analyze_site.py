#!/usr/bin/env python3
"""
震旦HR系統網站結構分析工具
分析登入頁面和打卡流程
"""

import asyncio
from playwright.async_api import async_playwright
from loguru import logger

async def analyze_aoacloud_site():
    """分析震旦HR系統網站結構"""
    
    async with async_playwright() as p:
        # 使用Chromium瀏覽器（在容器中較穩定）
        browser = await p.chromium.launch(
            headless=True,  # 無頭模式
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security'
            ]
        )
        
        try:
            page = await browser.new_page()
            
            # 設定User Agent避免被識別為機器人
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                             '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            logger.info("正在連接震旦HR系統...")
            
            # 訪問震旦HR系統
            response = await page.goto('https://erpline.aoacloud.com.tw', 
                                     wait_until='networkidle')
            
            if response:
                logger.info(f"頁面載入成功，狀態碼: {response.status}")
            
            # 等待頁面完全載入
            await page.wait_for_load_state('domcontentloaded')
            
            # 分析頁面標題
            title = await page.title()
            logger.info(f"頁面標題: {title}")
            
            # 分析登入表單元素
            logger.info("分析登入表單元素...")
            
            # 尋找可能的登入欄位
            login_selectors = [
                'input[type="text"]',
                'input[type="email"]', 
                'input[name*="user"]',
                'input[name*="login"]',
                'input[name*="account"]',
                'input[id*="user"]',
                'input[id*="login"]'
            ]
            
            password_selectors = [
                'input[type="password"]',
                'input[name*="pass"]',
                'input[name*="pwd"]',
                'input[id*="pass"]',
                'input[id*="pwd"]'
            ]
            
            # 檢查登入欄位
            for selector in login_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    for i, elem in enumerate(elements):
                        name = await elem.get_attribute('name')
                        id_attr = await elem.get_attribute('id')
                        placeholder = await elem.get_attribute('placeholder')
                        logger.info(f"找到可能的帳號欄位 {i+1}: name='{name}', id='{id_attr}', placeholder='{placeholder}'")
            
            # 檢查密碼欄位  
            for selector in password_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    for i, elem in enumerate(elements):
                        name = await elem.get_attribute('name')
                        id_attr = await elem.get_attribute('id')
                        placeholder = await elem.get_attribute('placeholder')
                        logger.info(f"找到密碼欄位 {i+1}: name='{name}', id='{id_attr}', placeholder='{placeholder}'")
            
            # 尋找登入按鈕
            button_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("登入")',
                'button:has-text("登錄")',
                'button:has-text("Login")',
                'input[value*="登入"]',
                'input[value*="登錄"]',
                'input[value*="Login"]'
            ]
            
            for selector in button_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        for i, elem in enumerate(elements):
                            text = await elem.inner_text()
                            value = await elem.get_attribute('value')
                            logger.info(f"找到可能的登入按鈕 {i+1}: text='{text}', value='{value}'")
                except Exception as e:
                    # 某些選擇器可能不支援，繼續嘗試其他的
                    continue
            
            # 截圖保存當前頁面
            await page.screenshot(path='login_page_analysis.png')
            logger.info("已保存登入頁面截圖: login_page_analysis.png")
            
            # 獲取頁面HTML結構（部分）
            html_content = await page.content()
            
            # 保存HTML內容用於進一步分析
            with open('login_page.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info("已保存頁面HTML: login_page.html")
            
        except Exception as e:
            logger.error(f"分析過程中發生錯誤: {e}")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    logger.info("開始分析震旦HR系統網站結構...")
    asyncio.run(analyze_aoacloud_site())
    logger.info("分析完成")