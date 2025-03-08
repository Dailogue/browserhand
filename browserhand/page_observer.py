import logging
from typing import Dict, List, Any
from playwright.async_api import ElementHandle

logger = logging.getLogger(__name__)

class PageObserver:
    @staticmethod
    async def is_element_in_viewport(element: ElementHandle) -> bool:
        try:
            if not await element.is_visible():
                return False
            return await element.evaluate("""element => {
                const rect = element.getBoundingClientRect();
                return rect.top >= 0 && rect.left >= 0 &&
                       rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                       rect.right <= (window.innerWidth || document.documentElement.clientWidth);
            }""")
        except Exception as e:
            logger.error(f"Viewport check error: {e}")
            return False

    @classmethod
    async def observe_frame(cls, frame) -> List[Dict[str, Any]]:
        results = []
        selectors = ["button", "a", "input", "select", "textarea", "[role='button']", "[role='link']", "[role='checkbox']"]
        for selector in selectors:
            try:
                elements = await frame.query_selector_all(selector)
                for element in elements:
                    try:
                        if not await element.is_visible():
                            continue
                        in_viewport = await cls.is_element_in_viewport(element)
                        text = (await element.inner_text()).strip()
                        elem_id = (await element.get_attribute("id") or "").strip()
                        elem_class = (await element.get_attribute("class") or "").strip()
                        element_info = {
                            "tag": await element.evaluate("el => el.tagName.toLowerCase()"),
                            "text": text,
                            "id": elem_id,
                            "class": elem_class,
                            "is_visible": True,
                            "in_viewport": in_viewport,
                            "is_enabled": await element.is_enabled() if hasattr(element, "is_enabled") else True,
                        }
                        if element_info["tag"] == "a":
                            href = await element.get_attribute("href")
                            if href:
                                element_info["href"] = href
                        if element_info["tag"] == "input":
                            element_info["type"] = (await element.get_attribute("type")) or "text"
                        if element_info["tag"] in ["input", "textarea"]:
                            placeholder = await element.get_attribute("placeholder")
                            if placeholder:
                                element_info["placeholder"] = placeholder
                        if in_viewport and (text or elem_id or elem_class or element_info.get("href") or (element_info.get("tag") == "input" and element_info.get("type") != "text") or element_info.get("placeholder")):
                            element_info["frame"] = frame.url
                            results.append(element_info)
                    except Exception as e:
                        logger.error(f"Frame element processing error: {e}")
            except Exception as e:
                logger.error(f"Error querying selector {selector} in frame: {e}")
        logger.info(f"Observed {len(results)} elements in frame")
        return results

    @classmethod
    async def observe_page(cls, page) -> List[Dict[str, Any]]:
        results = []
        selectors = ["button", "a", "input", "select", "textarea", "[role='button']", "[role='link']", "[role='checkbox']"]
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    try:
                        if not await element.is_visible():
                            continue
                        in_viewport = await cls.is_element_in_viewport(element)
                        text = (await element.inner_text()).strip()
                        elem_id = (await element.get_attribute("id") or "").strip()
                        elem_class = (await element.get_attribute("class") or "").strip()
                        element_info = {
                            "tag": await element.evaluate("el => el.tagName.toLowerCase()"),
                            "text": text,
                            "id": elem_id,
                            "class": elem_class,
                            "is_visible": True,
                            "in_viewport": in_viewport,
                            "is_enabled": await element.is_enabled() if hasattr(element, "is_enabled") else True,
                        }
                        if element_info["tag"] == "a":
                            href = await element.get_attribute("href")
                            if href:
                                element_info["href"] = href
                        if element_info["tag"] == "input":
                            element_info["type"] = (await element.get_attribute("type")) or "text"
                        if element_info["tag"] in ["input", "textarea"]:
                            placeholder = await element.get_attribute("placeholder")
                            if placeholder:
                                element_info["placeholder"] = placeholder
                        if in_viewport and (text or elem_id or elem_class or element_info.get("href") or (element_info.get("tag") == "input" and element_info.get("type") != "text") or element_info.get("placeholder")):
                            results.append(element_info)
                    except Exception as e:
                        logger.error(f"Page element processing error: {e}")
            except Exception as e:
                logger.error(f"Error querying selector {selector}: {e}")
        for frame in page.frames:
            if frame != page.main_frame:
                try:
                    results.extend(await cls.observe_frame(frame))
                except Exception as e:
                    logger.error(f"Error observing frame {frame.url}: {e}")
        logger.info(f"Observed {len(results)} elements in viewport")            
        return results
