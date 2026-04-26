#!/usr/bin/env python3
"""Convert HTML screenshots to PNG using Playwright."""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = Path("/home/z/my-project/download/OmniVoice-Mobile/demo/screenshots")
DEMO_DIR = Path("/home/z/my-project/download/OmniVoice-Mobile/demo")

FILES = ["install.html", "info.html", "help.html", "generate.html", "clone.html"]


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 800, "height": 600})

        for fname in FILES:
            html_path = DEMO_DIR / fname
            png_path = SCREENSHOTS_DIR / fname.replace(".html", ".png")

            if not html_path.exists():
                print(f"  SKIP {fname} (not found)")
                continue

            await page.goto(f"file://{html_path}")
            # Wait for rendering
            await page.wait_for_timeout(500)
            
            # Auto-size to content
            height = await page.evaluate("document.body.scrollHeight")
            await page.set_viewport_size({"width": 800, "height": min(height + 40, 2000)})
            await page.wait_for_timeout(300)

            await page.screenshot(path=str(png_path), full_page=True)
            size = png_path.stat().st_size
            print(f"  [OK] {fname} -> {png_path.name} ({size//1024} KB)")

        await browser.close()
        print(f"\nAll screenshots saved to: {SCREENSHOTS_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
