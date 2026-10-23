import unittest
import urllib.error
from unittest.mock import patch

import check_status as checker


class StreamChecks(unittest.TestCase):
    def setUp(self):
        self.cors = {'Access-Control-Allow-Origin': '*'}
        self.media = b'\x47' + bytes(187) + b'\x47' + bytes(187) + b'\x47' + bytes(187)
        self.playlist = b'#EXTM3U\n#EXTINF:5,\nold.ts\n#EXTINF:5,\nnew.ts\n'

    def test_embedded_channel_sends_required_headers_and_checks_media(self):
        channel = next(ch for ch in checker.CHANNELS if ch['name'] == 'TBS')
        with patch.object(checker, 'fetch', side_effect=[
            (self.playlist, {}, channel['checkUrl']), (self.media, {}, 'https://media/new.ts')
        ]) as fetch:
            self.assertTrue(checker.check_stream(channel))
            self.assertEqual(fetch.call_args_list[0].args[0], channel['checkUrl'])
            for call in fetch.call_args_list:
                self.assertEqual(call.args[1]['Referer'], 'https://mov3.co/')
                self.assertEqual(call.args[1]['Origin'], 'https://mov3.co')
            self.assertTrue(fetch.call_args_list[1].args[0].endswith('/new.ts'))

    def test_master_playlist_checks_cors_and_resolves_redirects(self):
        with patch.object(checker, 'fetch', side_effect=[
            (b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000\nlow/index.m3u8\n', self.cors, 'https://cdn/master.m3u8'),
            (self.playlist, self.cors, 'https://cdn/redirected/media.m3u8'),
            (self.media, self.cors, 'https://cdn/redirected/new.ts'),
        ]) as fetch:
            self.assertTrue(checker.check_stream({'url': 'https://origin/master.m3u8'}))
            self.assertEqual(fetch.call_args_list[1].args[0], 'https://cdn/low/index.m3u8')
            self.assertEqual(fetch.call_args_list[2].args[0], 'https://cdn/redirected/new.ts')

    def test_unrelated_cors_origin_is_rejected(self):
        self.assertFalse(checker.is_cors_ok({'Access-Control-Allow-Origin': 'https://other.example'}))
        self.assertTrue(checker.is_cors_ok({'Access-Control-Allow-Origin': checker.APP_ORIGIN}))

    def test_segment_also_requires_cors_for_in_app_playback(self):
        with patch.object(checker, 'fetch', side_effect=[
            (self.playlist, self.cors, 'https://cdn/index.m3u8'), (self.media, {}, 'https://cdn/new.ts')
        ]):
            self.assertFalse(checker.check_stream({'url': 'https://cdn/index.m3u8'}))

    def test_html_instead_of_video_is_rejected(self):
        with patch.object(checker, 'fetch', side_effect=[
            (self.playlist, self.cors, 'https://cdn/index.m3u8'),
            (b'<html>Stream unavailable</html>', self.cors, 'https://cdn/new.ts')
        ]):
            self.assertFalse(checker.check_stream({'url': 'https://cdn/index.m3u8'}))

    def test_empty_master_is_not_live(self):
        with patch.object(checker, 'fetch', return_value=(
            b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000\n', self.cors, 'https://cdn/index.m3u8'
        )):
            self.assertFalse(checker.check_stream({'url': 'https://cdn/index.m3u8'}))

    def test_transport_failure_is_unknown(self):
        with patch.object(checker, 'fetch', side_effect=urllib.error.URLError('DNS failure')):
            self.assertEqual(checker.check_channel({'name': 'Test', 'url': 'https://cdn/index.m3u8'}), ('Test', 'unknown'))

    def test_web_page_without_stream_is_unknown(self):
        with patch.object(checker, 'fetch') as fetch:
            self.assertEqual(checker.check_channel({'name': 'Test', 'url': 'https://cdn/player.html'}), ('Test', 'unknown'))
            fetch.assert_not_called()

    def test_vlc_playlist_matches_current_terrestrial_sources(self):
        text = (checker.ROOT / 'japan-tv-vlc.m3u').read_text(encoding='utf-8')
        sources = [ch['checkUrl'] for ch in checker.CHANNELS if ch.get('embed')]
        self.assertTrue(text.startswith('#EXTM3U\n'))
        self.assertEqual([line for line in text.splitlines() if line.startswith('https://')], sources)
        self.assertEqual(text.count('#EXTVLCOPT:http-referrer=https://mov3.co/'), len(sources))


if __name__ == '__main__':
    unittest.main()
