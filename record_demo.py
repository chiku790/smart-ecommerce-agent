import asyncio
import os
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

FRONTEND_URL = "https://smart-ecommerce-frontend-40148140586.us-east1.run.app"
RECORD_DIR = Path("/config/.gemini/antigravity/scratch/smart-ecommerce/recordings")

async def record_demo():
    if RECORD_DIR.exists():
        shutil.rmtree(RECORD_DIR)
    RECORD_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(RECORD_DIR),
            record_video_size={"width": 1280, "height": 720}
        )

        page = await context.new_page()
        print(f"Navigating to {FRONTEND_URL}...")
        await page.goto(FRONTEND_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # 1. First prompt: Core app showcase (Search products & store pickup)
        first_prompt = "Find ergonomic desk chairs under $300 and find store pickup locations near Seattle"
        print(f"Submitting 1st prompt: {first_prompt}")
        
        # Click input field, type with realistic delay
        await page.click("#input")
        await page.type("#input", first_prompt, delay=40)
        await page.wait_for_timeout(500)
        await page.keyboard.press("Enter")

        # Wait for agent response message to appear
        print("Waiting for agent 1st response...")
        await page.wait_for_selector(".msg-row.agent", timeout=45000)
        await page.wait_for_timeout(6000)

        # 2. Second prompt: Richer prompt showing tool call & image generation
        second_prompt = "Generate a sleek modern image of the ergonomic desk chair and add 1 to my cart"
        print(f"Submitting 2nd prompt: {second_prompt}")

        await page.click("#input")
        await page.type("#input", second_prompt, delay=40)
        await page.wait_for_timeout(500)
        await page.keyboard.press("Enter")

        # Wait for agent 2nd response message with image
        print("Waiting for agent 2nd response with image...")
        await page.wait_for_selector(".msg-row.agent:nth-of-type(4)", timeout=60000)
        await page.wait_for_timeout(8000)

        # Scroll down to ensure full dialogue is visible
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(4000)

        video_path = await page.video.path()
        print(f"Video captured at raw path: {video_path}")

        await context.close()
        await browser.close()

        target_file = RECORD_DIR / "agent_demo.webm"
        if os.path.exists(video_path):
            shutil.copy(video_path, target_file)
            print(f"Demo video saved to: {target_file}")
            return target_file
        return None

if __name__ == "__main__":
    asyncio.run(record_demo())
