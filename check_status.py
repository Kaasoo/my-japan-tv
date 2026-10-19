"""Check the same channel definitions used by the static web app."""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parent
APP_ORIGIN = 'https://kaasoo.github.io'
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Origin': APP_ORIGIN}


def load_channels():
    # channels.js contains a JSON array assigned to window.CHANNELS.
    source = (ROOT / 'channels.js').read_text(encoding='utf-8')
    return json.loads(source[source.index('['):source.rindex(']') + 1])


CHANNELS = load_channels()


def is_cors_ok(headers, origin=APP_ORIGIN):
    return headers.get('Access-Control-Allow-Origin', '').strip() in ('*', origin)


def fetch(url, headers, max_bytes=131072, timeout=15):
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise ValueError(f'Unexpected HTTP status: {response.status}')
        return response.read(max_bytes), response.headers, response.url


def is_media(data):
    # MPEG-TS or ISO BMFF media, never an HTML error page returning 200.
    transport_stream = len(data) >= 377 and all(data[i] == 0x47 for i in (0, 188, 376))
    fragment = len(data) >= 8 and data[4:8] in (b'ftyp', b'styp', b'moof', b'sidx')
    return transport_stream or fragment


def check_stream(channel):
    headers = {**HEADERS, **channel.get('requestHeaders', {})}
    url = channel.get('checkUrl', channel['url'])
    # External players use their own origin; in-app video requires our origin.
    require_cors = not channel.get('link', False)
    for _ in range(4):
        data, response_headers, base = fetch(url, headers)
        text = data.decode('utf-8', errors='replace')
        if not text.lstrip().startswith('#EXTM3U'):
            return False
        if require_cors and not is_cors_ok(response_headers):
            return False
        lines = [line.strip() for line in text.splitlines()]
        urls = [line for line in lines if line and not line.startswith('#')]
        if not urls:
            return False
        if any(line.startswith('#EXT-X-STREAM-INF:') for line in lines):
            url = urllib.parse.urljoin(base, urls[0])
            continue
        if not any(line.startswith('#EXTINF:') for line in lines):
            return False
        # Check newest complete media using the final URL after redirects.
        data, segment_headers, _ = fetch(urllib.parse.urljoin(base, urls[-1]), headers, 1024)
        return is_media(data) and (not require_cors or is_cors_ok(segment_headers))
    return False


def check_channel(channel):
    url = channel.get('checkUrl', channel['url'])
    try:
        # A successful web page response alone does not prove its video is live.
        status = ('live' if check_stream(channel) else 'offline') if '.m3u8' in url else 'unknown'
    except urllib.error.HTTPError as error:
        print(f"{channel['name']}: HTTP {error.code}")
        status = 'offline' if error.code in (404, 410) else 'unknown'
    except (urllib.error.URLError, OSError, ValueError) as error:
        print(f"{channel['name']}: {error}")
        status = 'unknown'
    print(f"{channel['name']}: {status.upper()}", flush=True)
    return channel['name'], status


def main():
    statuses = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(check_channel, channel) for channel in CHANNELS]
        for future in as_completed(futures):
            name, status = future.result()
            statuses[name] = status
    result = {
        'updated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'channels': statuses,
    }
    temporary = ROOT / 'status.js.tmp'
    temporary.write_text('window.STATUS = ' + json.dumps(result, ensure_ascii=False) + ';\n', encoding='utf-8')
    temporary.replace(ROOT / 'status.js')
    print(f"Saved: {sum(s == 'live' for s in statuses.values())}/{len(CHANNELS)} live")


if __name__ == '__main__':
    main()
