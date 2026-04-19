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
    {"name": "FUJI TV",     "url": "https://fujitv4.mov3.co/hls/fujitv.m3u8"},
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

def fetch_text(url, timeout=12, method='GET', max_bytes=2048):
    """URL을 요청해서 텍스트를 반환. 실패시 None."""
    try:
        req = urllib.request.Request(url, headers=HEADERS, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return resp.read(max_bytes).decode('utf-8', errors='ignore')
    except Exception:
        pass
    return None

def resolve_url(base_url, path):
    """상대경로를 절대 URL로 변환."""
    if path.startswith('http://') or path.startswith('https://'):
        return path
    # base_url에서 마지막 '/' 이전까지 추출
    base = base_url.rsplit('/', 1)[0]
    return base + '/' + path

def check_segment(seg_url, timeout=10):
    """세그먼트 URL이 실제로 접근 가능한지 HEAD 요청으로 확인."""
    try:
        req = urllib.request.Request(seg_url, headers=HEADERS, method='HEAD')
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        pass
    return False

# CDN 도메인은 세그먼트에 토큰/세션이 필요해 HEAD 요청이 막히는 경우가 있음
# → variant m3u8까지만 확인하고 세그먼트 체크는 생략
CDN_DOMAINS = ('akamaized.net', 'cloudfront.net', 'fastly.net', 'nhkworld.jp')

def is_cdn_url(url):
    return any(d in url for d in CDN_DOMAINS)

def check_m3u8(url, timeout=12):
    """
    m3u8 URL의 스트림 상태를 최대 3단계로 확인:
      1단계: m3u8 파일 접근 가능 여부 (HTTP 200 + #EXTM3U)
      2단계: 마스터 플레이리스트라면 첫 번째 variant URL로 이동 후 접근 확인
      3단계: CDN이 아닌 경우에만 실제 .ts 세그먼트 HEAD 요청으로 최종 확인
    """
    content = fetch_text(url, timeout=timeout)
    if not content:
        return False
    if '#EXTM3U' not in content:
        return False

    # --- 2단계: 마스터 플레이리스트 처리 ---
    if '#EXT-X-STREAM-INF' in content:
        variant_url = None
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                variant_url = resolve_url(url, line)
                break
        if not variant_url:
            return True
        # CDN variant는 URL 접근만 확인 (세그먼트 체크 불필요)
        if is_cdn_url(variant_url):
            variant_content = fetch_text(variant_url, timeout=timeout)
            return bool(variant_content and '#EXTM3U' in variant_content)
        content = fetch_text(variant_url, timeout=timeout)
        if not content:
            return False
        url = variant_url

    # --- 3단계: 세그먼트 확인 (CDN이 아닌 경우만) ---
    if '#EXTINF' not in content:
        return True

    # CDN 기반 미디어 플레이리스트는 세그먼트 체크 생략
    if is_cdn_url(url):
        return True

    seg_url = None
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            seg_url = resolve_url(url, line)
            break

    if not seg_url:
        return True

    return check_segment(seg_url)

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

    js_path = os.path.join(current_dir, 'status.js')
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write("window.STATUS = " + json.dumps(result, ensure_ascii=False) + ";\n")
    print(f"✅ status.js 저장 완료")

if __name__ == "__main__":
    main()
