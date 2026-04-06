import asyncio
import json
import os
from playwright.async_api import async_playwright

async def get_video_src(page, channel_name, url):
    try:
        print(f"[{channel_name}] 소스 추출 시도 중...")
        # 타임아웃 40초, DOM 구조 로딩 시 바로 진행하여 속도 향상
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        
        # 자바스크립트가 iframe을 생성할 시간을 충분히 줌 (5초)
        await asyncio.sleep(5)
        
        # 영상 플레이어가 담긴 iframe(id='su-ivp') 찾기
        iframe = await page.query_selector("#su-ivp")
        
        if iframe:
            src = await iframe.get_attribute("src")
            if not src: return None

            # --- [주소 정규화 로직] ---
            
            # 1. //ok.ru... 처럼 프로토콜만 없는 경우 보정
            if src.startswith('//'):
                src = "https:" + src
            
            # 2. embedfujitv.html 처럼 도메인이 없는 상대 경로인 경우 보정
            elif not src.startswith('http'):
                if src.startswith('/'):
                    src = "https://mov3.co" + src
                else:
                    src = "https://mov3.co/" + src
            
            # 3. 중복 도메인 방지 (mov3.co//ok.ru 같은 케이스 처리)
            if "mov3.co" in src and "ok.ru" in src:
                src = "https://ok.ru" + src.split("ok.ru")[1]
            
            print(f"✅ {channel_name} 추출 성공: {src}")
            return src
        else:
            print(f"❌ {channel_name}: #su-ivp 요소를 찾을 수 없음")
            return None
            
    except Exception as e:
        print(f"⚠️ {channel_name} 에러 발생: {e}")
        return None

async def main():
    # [중요] GitHub Actions 환경에서도 파일 위치를 정확히 잡기 위한 경로 설정
    # 이 코드가 있는 폴더의 절대 경로를 가져와서 그 옆에 channels.json을 만듭니다.
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
        # headless=True: 창을 띄우지 않고 백그라운드에서 실행 (GitHub Actions용)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 일반 브라우저처럼 보이게 하기 위한 헤더 설정
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        for ch in channels_to_fetch:
            src = await get_video_src(page, ch['name'], ch['url'])
            if src:
                results.append({ "name": ch['name'], "url": src })
            else:
                print(f"⏩ {ch['name']} 추출 실패로 목록에서 제외")
        
        await browser.close()

    # 결과가 있을 때만 파일 저장
    if results:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✨ 업데이트 완료! 저장 위치: {json_path}")
    else:
        print("\n⚠️ 추출된 데이터가 없어 파일을 업데이트하지 않았습니다.")

if __name__ == "__main__":
    asyncio.run(main())