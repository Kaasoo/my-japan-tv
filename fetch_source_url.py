import asyncio
import json
import os
from playwright.async_api import async_playwright

async def get_video_src(page, channel_name, url):
    try:
        print(f"[{channel_name}] 추출 시도 중...")
        # 타임아웃을 피하기 위해 domcontentloaded만 기다림
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(5)  # 자바스크립트 실행을 위한 여유 시간
        
        iframe = await page.query_selector("#su-ivp")
        if iframe:
            src = await iframe.get_attribute("src")
            # 상대 경로일 경우 도메인 붙여주기
            if src.startswith('/'):
                src = "https://mov3.co" + src
            return src
        return None
    except Exception as e:
        print(f"⚠️ {channel_name} 에러: {e}")
        return None

async def main():
    channels_to_fetch = [
        { "name": "NHK G", "url": "https://mov3.co/nhk.html?nochat=1" },
        { "name": "TV ASAHI", "url": "https://mov3.co/tvasahi.html?nochat=1" },
        { "name": "TV TOKYO", "url": "https://mov3.co/tvtokyo.html?nochat=1" },
        { "name": "NTV", "url": "https://mov3.co/ntv.html?nochat=1" },
        { "name": "FUJI TV", "url": "https://mov3.co/fujitv.html?nochat=1" },
        { "name": "TBS", "url": "https://mov3.co/tbs.html?nochat=1" },
        { "name": "Tokyo MX", "url": "https://mov3.co/tokyomx.html?nochat=1" }
    ]

    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for ch in channels_to_fetch:
            src = await get_video_src(page, ch['name'], ch['url'])
            if src:
                print(f"✅ {ch['name']} 추출 성공: {src}")
                results.append({ "name": ch['name'], "url": src })
            else:
                # 실패 시 기존 값을 유지하거나 기본값 설정 (여기서는 생략)
                print(f"❌ {ch['name']} 추출 실패")
        
        await browser.close()

    # JSON 파일로 저장
    with open('channels.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n✨ channels.json 파일이 업데이트되었습니다.")

if __name__ == "__main__":
    asyncio.run(main())