import sys
import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# Windows 콘솔 인코딩 보정 (GitHub Actions Ubuntu는 이미 UTF-8)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 확인할 채널 목록 (channels.js와 동일하게 유지)
CHANNELS = [
    {"name": "NHK G",       "url": "https://nl.utako.moe/NHK_G/index.m3u8"},
    {"name": "NHK E テレ",  "url": "https://nl.utako.moe/NHK_E/index.m3u8"},
    {"name": "NTV",         "url": "https://nl.utako.moe/Nippon_TV/index.m3u8"},
    {"name": "TV ASAHI",    "url": "https://nl.utako.moe/TV_Asahi/index.m3u8"},
    {"name": "TBS",         "url": "https://nl.utako.moe/TBS/index.m3u8"},
    {"name": "TV TOKYO",    "url": "https://nl.utako.moe/TV_Tokyo/index.m3u8"},
    {"name": "FUJI TV",     "url": "https://nl.utako.moe/Fuji_TV/index.m3u8"},
    {"name": "Tokyo MX",    "url": "https://nl.utako.moe/Tokyo_MX1/index.m3u8"},
    {"name": "MBS",         "url": "https://nl.utako.moe/mbs/index.m3u8"},
    {"name": "ABC TV",      "url": "https://nl.utako.moe/abc/index.m3u8"},
    {"name": "関西TV",      "url": "https://nl.utako.moe/kansaitv/index.m3u8"},
    {"name": "ytv",         "url": "https://nl.utako.moe/ytv/index.m3u8"},
    {"name": "NHK World",   "url": "https://master.nhkworld.jp/nhkworld-tv/playlist/live.m3u8"},
    {"name": "Weathernews", "url": "https://rch01e-alive-hls.akamaized.net/38fb45b25cdb05a1/out/v1/4e907bfabc684a1dae10df8431a84d21/index.m3u8"},
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Referer': 'https://web.utako.moe/',
}

def check_m3u8(url, timeout=12):
    """m3u8 URL에 요청을 보내 스트림이 살아있는지 확인합니다."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                content = resp.read(512).decode('utf-8', errors='ignore')
                return '#EXTM3U' in content or '#EXT-X-STREAM-INF' in content or '#EXTINF' in content
    except Exception:
        pass
    return False

def check_embed(url, timeout=12):
    """iframe embed URL의 HTTP 상태를 확인합니다."""
    try:
        req = urllib.request.Request(url, headers=HEADERS, method='HEAD')
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        pass
    return False

def check_channel(ch):
    url = ch['url']
    is_live = check_m3u8(url) if '.m3u8' in url else check_embed(url)
    status = 'live' if is_live else 'offline'
    icon = '✅' if is_live else '❌'
    print(f"{icon} {ch['name']}: {status.upper()}")
    return ch['name'], status

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"🔍 {len(CHANNELS)}개 채널 상태 확인 중...\n")

    statuses = {}

    # 병렬로 모든 채널을 동시 확인 (속도 향상)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(check_channel, ch): ch for ch in CHANNELS}
        for future in as_completed(futures):
            name, status = future.result()
            statuses[name] = status

    live_count = sum(1 for s in statuses.values() if s == 'live')
    print(f"\n📊 결과: {live_count}/{len(CHANNELS)}개 채널 방송 중")

    result = {
        'updated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'channels': statuses,
    }

    # status.js 저장 (index.html 파일 직접 열기 호환)
    js_path = os.path.join(current_dir, 'status.js')
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write("window.STATUS = " + json.dumps(result, ensure_ascii=False) + ";\n")
    print(f"✅ status.js 저장 완료")

if __name__ == "__main__":
    main()
