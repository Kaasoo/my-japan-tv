import json
import os

# 모든 채널을 utako.moe 직접 m3u8 스트림으로 관리합니다.
# Playwright 스크래핑 불필요 — URL이 안정적이므로 정적 목록으로 유지합니다.

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

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))

    json_path = os.path.join(current_dir, 'channels.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(CHANNELS, f, ensure_ascii=False, indent=2)
    print(f"✅ channels.json 저장 완료")

    js_path = os.path.join(current_dir, 'channels.js')
    js_content = "window.CHANNELS = " + json.dumps(CHANNELS, ensure_ascii=False, indent=2) + ";\n"
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(js_content)
    print(f"✅ channels.js 저장 완료")

    print(f"\n✨ 총 {len(CHANNELS)}개 채널 업데이트 완료!")

if __name__ == "__main__":
    main()
