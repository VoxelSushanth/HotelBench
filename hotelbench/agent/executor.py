"""
HotelBench Executor Module
Playwright action executor with screenshot capture
"""

import base64
import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from config import (
    BROWSER_VIEWPORT_WIDTH,
    BROWSER_VIEWPORT_HEIGHT,
    NETWORK_IDLE_TIMEOUT,
    ACTION_SETTLE_WAIT,
    ACTION_TIMEOUT,
    SCREENSHOT_TIMEOUT,
    SCROLL_PIXELS,
    PMS_UI_URL,
)


class PlaywrightExecutor:
    """Async Playwright executor for browser automation."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    async def start(self):
        """Initialize Playwright and open the PMS UI."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={"width": BROWSER_VIEWPORT_WIDTH, "height": BROWSER_VIEWPORT_HEIGHT}
        )
        self.page = await self.context.new_page()
        await self.page.goto(PMS_UI_URL)
        await self.page.wait_for_load_state("networkidle")
    
    async def stop(self):
        """Close the browser and cleanup."""
        if self.browser:
            await self.browser.close()
    
    async def take_screenshot(self) -> str:
        """Take a full-page screenshot and return as base64 PNG."""
        try:
            screenshot = await self.page.screenshot(
                full_page=True,
                format="png",
                timeout=SCREENSHOT_TIMEOUT
            )
            return base64.b64encode(screenshot).decode("utf-8")
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            raise
    
    async def wait_for_idle(self):
        """Wait for network to be idle."""
        try:
            await self.page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT)
        except Exception:
            pass  # Continue even if timeout
    
    async def settle(self):
        """Wait for JS state to settle after an action."""
        await asyncio.sleep(ACTION_SETTLE_WAIT / 1000)
    
    async def execute_action(self, action_type: str, target: str, value: str = "") -> dict:
        """Execute a single action and return result."""
        await self.wait_for_idle()
        
        try:
            if action_type == "click":
                return await self._click(target)
            elif action_type == "type":
                return await self._type(target, value)
            elif action_type == "select":
                return await self._select(target, value)
            elif action_type == "scroll":
                return await self._scroll()
            elif action_type == "navigate_tab":
                return await self._navigate_tab(value)
            else:
                return {"success": False, "error": f"Unknown action type: {action_type}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _click(self, selector: str) -> dict:
        """Click an element by selector with fallback chain."""
        selectors = self._get_selector_chain(selector)
        
        for sel in selectors:
            try:
                await self.page.click(sel, timeout=ACTION_TIMEOUT)
                await self.settle()
                return {"success": True, "selector_used": sel}
            except Exception:
                continue
        
        return {"success": False, "error": "selector_not_found"}
    
    async def _type(self, selector: str, value: str) -> dict:
        """Fill an input field with text."""
        selectors = self._get_selector_chain(selector)
        
        for sel in selectors:
            try:
                await self.page.fill(sel, value, timeout=ACTION_TIMEOUT)
                await self.page.press(sel, "Tab")
                await self.settle()
                return {"success": True, "selector_used": sel}
            except Exception:
                continue
        
        return {"success": False, "error": "selector_not_found"}
    
    async def _select(self, selector: str, value: str) -> dict:
        """Select an option from a dropdown."""
        selectors = self._get_selector_chain(selector)
        
        for sel in selectors:
            try:
                await self.page.select_option(sel, value, timeout=ACTION_TIMEOUT)
                await self.settle()
                return {"success": True, "selector_used": sel}
            except Exception:
                continue
        
        return {"success": False, "error": "selector_not_found"}
    
    async def _scroll(self) -> dict:
        """Scroll down the page by SCROLL_PIXELS."""
        try:
            await self.page.evaluate(f"window.scrollBy(0, {SCROLL_PIXELS})")
            await self.settle()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _navigate_tab(self, tab_name: str) -> dict:
        """Navigate to a different tab."""
        selector = f'[data-tab="{tab_name}"]'
        return await self._click(selector)
    
    def _get_selector_chain(self, primary_selector: str) -> list[str]:
        """Generate a fallback chain of selectors."""
        selectors = [primary_selector]
        
        # If it's a data-testid, add aria-label and nth-match fallbacks
        if primary_selector.startswith('[data-testid="'):
            test_id = primary_selector.split('"')[1]
            selectors.append(f'[aria-label*="{test_id}"]')
            selectors.append(f'text={test_id}')
            selectors.append(f'[data-testid*="{test_id.split("-")[0]}"]')
        
        # Add nth-match as last resort
        selectors.append(f"{primary_selector} >> nth=0")
        
        return selectors
    
    async def get_current_tab(self) -> str:
        """Get the current active tab name."""
        try:
            active_tab = await self.page.query_selector('.tab-btn.active')
            if active_tab:
                tab_id = await active_tab.get_attribute('data-tab')
                return tab_id or "unknown"
            return "unknown"
        except Exception:
            return "unknown"
    
    async def reset_pms(self):
        """Reset the PMS UI to initial state by reloading."""
        await self.page.reload()
        await self.page.wait_for_load_state("networkidle")
        await self.settle()


# Global executor instance (for singleton pattern)
_executor: Optional[PlaywrightExecutor] = None


async def get_executor(headless: bool = True) -> PlaywrightExecutor:
    """Get or create the global executor instance."""
    global _executor
    if _executor is None:
        _executor = PlaywrightExecutor(headless=headless)
        await _executor.start()
    return _executor


async def shutdown_executor():
    """Shutdown the global executor instance."""
    global _executor
    if _executor:
        await _executor.stop()
        _executor = None
