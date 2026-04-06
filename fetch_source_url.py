import asyncio
import json
import os
from playwright.async_api import async_playwright

async def get_video_src(page, channel_name, url):
    try:
        print(f"[{channel_name}] 소스 추출 시도 중...")
        # 페이지 로딩 타임아웃 40초, DOM 구조 로드 시 바로 진행
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        
        # 자바스크립트가 iframe을 생성할 시간을 충분히 줌 (5초)
        await asyncio.sleep(5)
        
        # 영상이 담긴 iframe(id='su-ivp') 찾기
        iframe = await page.query_selector("#su-ivp")
        
        if iframe:
            src = await iframe.get_attribute("src")
            if not src: return None

            # --- [주소 정규화 로직 시작] ---
            
            # 1. //ok.ru... 처럼 프로토콜만 없는 경우
            if src.startswith('//'):
                src = "https:" + src
            
            # 2. embedfujitv.html 처럼 상대 경로인 경우
            elif not src.startswith('http'):
                # 슬래시 유무에 따라 도메인 결합
                if src.startswith('/'):
                    src = "https://mov3.co" + src
                else:
                    src = "https://mov3.co/" + src
            
            # 3. 중복된 슬래시나 도메인 꼬임 방지 (mov3.co//ok.ru 방지)
            if "mov3.co" in src and "ok.ru" in src:
                # ok.ru는 독립 도메인이므로 mov3 부분을 제거
                src = "https://ok.ru" + src.split("ok.ru")[1]
            
            # --- [주소 정규화 로직 끝] ---
            
            print(f"✅ {channel_name} 추출 성공: {src}")
            return src
        else:
            print(f"❌ {channel_name}: #su-ivp 요소를 찾을 수 없음")
            return None
            
    except Exception as e:
        print(f"⚠️ {channel_name} 에러 발생: {e}")
        return None

async def main():
    # 현재 파이썬 파일이 있는 폴더 경로를 찾아서 저장 위치로 지정
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, 'channels.json')

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
        # 브라우저 실행 (실제 창을 보고 싶으면 headless=False로 변경하세요)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 차단 방지를 위한 User-Agent 설정
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        for ch in channels_to_fetch:
            src = await get_video_src(page, ch['name'], ch['url'])
            if src:
                results.append({ "name": ch['name'], "url": src })
            else:
                print(f"⏩ {ch['name']}는 건너뜁니다.")
        
        await browser.close()

    # 추출된 데이터를 JSON 파일로 저장 (파이썬 파일과 동일 위치)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✨ 작업 완료! 저장 위치: {json_path}")

if __name__ == "__main__":
    asyncio.run(main())