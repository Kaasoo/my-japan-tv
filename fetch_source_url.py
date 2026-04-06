import asyncio
from playwright.async_api import async_playwright

async def get_video_src(channel_name, url):
    async with async_playwright() as p:
        # 브라우저 실행 (headless=True는 창을 띄우지 않음)
        browser = await p.chromium.launch(headless=True)
        # 모바일인 척 속이기 위해 User Agent 설정
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"[{channel_name}] 소스 추출 중...")
            await page.goto(url, wait_until="networkidle")
            
            # id='su-ivp' 요소가 나타날 때까지 최대 10초 대기
            iframe_element = await page.wait_for_selector("#su-ivp", timeout=10000)
            
            if iframe_element:
                src = await iframe_element.get_attribute("src")
                print(f"✅ {channel_name} 원본 주소: {src}")
                return src
            else:
                print(f"❌ {channel_name}: 요소를 찾을 수 없습니다.")
        except Exception as e:
            print(f"⚠️ {channel_name} 에러 발생: {e}")
        finally:
            await browser.close()

async def main():
    channels = [
        { "name": "NHK G", "url": "https://mov3.co/nhk.html?nochat=1" },
        { "name": "TV ASAHI", "url": "https://mov3.co/tvasahi.html?nochat=1" },
        { "name": "TV TOKYO", "url": "https://mov3.co/tvtokyo.html?nochat=1" },
        { "name": "NTV", "url": "https://mov3.co/ntv.html?nochat=1" },
        { "name": "FUJI TV", "url": "https://mov3.co/fujitv.html?nochat=1" },
        { "name": "TBS", "url": "https://mov3.co/tbs.html?nochat=1" },
        { "name": "Tokyo MX", "url": "https://mov3.co/tokyomx.html?nochat=1" }
    ]

    for ch in channels:
        await get_video_src(ch['name'], ch['url'])

if __name__ == "__main__":
    asyncio.run(main())