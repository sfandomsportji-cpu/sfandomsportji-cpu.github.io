import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import importlib.util

MODULE_PATH = Path(__file__).resolve().parents[1] / "sync_blogger.py"
spec = importlib.util.spec_from_file_location("sync_blogger", MODULE_PATH)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

VALID_ATOM = b'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>SFANDOM TEST</title>
  <entry>
    <title>Safe Test Post</title>
    <published>2026-09-14T10:00:00Z</published>
    <link rel="alternate" href="https://example.blogspot.com/2026/09/test.html" />
    <category term="MLB" />
    <content type="html">&lt;p&gt;Hello&lt;/p&gt;&lt;script&gt;bad()&lt;/script&gt;&lt;img src="https://blogger.googleusercontent.com/img/test.jpg"&gt;</content>
  </entry>
</feed>'''

VALID_RSS = b'''<?xml version="1.0"?>
<rss version="2.0"><channel><title>SFANDOM TEST</title>
<item><title>RSS Test</title><link>https://example.blogspot.com/2026/09/rss.html</link>
<pubDate>Mon, 14 Sep 2026 10:00:00 GMT</pubDate><category>FEATURE</category>
<description>&lt;b&gt;Safe text&lt;/b&gt;</description></item>
</channel></rss>'''


class BridgeSafetyTests(unittest.TestCase):
    def test_valid_atom_is_text_only(self):
        posts = bridge.parse_feed(VALID_ATOM)
        bridge.validate(posts)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["title"], "Safe Test Post")
        self.assertNotIn("<script>", posts[0]["summary"])
        self.assertNotIn("<p>", posts[0]["summary"])
        self.assertEqual(posts[0]["labels"], ["MLB"])

    def test_valid_rss(self):
        posts = bridge.parse_feed(VALID_RSS)
        bridge.validate(posts)
        self.assertEqual(posts[0]["title"], "RSS Test")
        self.assertEqual(posts[0]["summary"], "Safe text")

    def test_malformed_xml_is_rejected(self):
        with self.assertRaises(ValueError):
            bridge.parse_feed(b"<feed><entry>")

    def test_empty_feed_is_rejected(self):
        empty = b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'''
        with self.assertRaises(ValueError):
            bridge.parse_feed(empty)

    def test_javascript_url_is_rejected(self):
        self.assertIsNone(bridge.safe_url("javascript:alert(1)"))

    def test_atomic_write_replaces_only_after_complete_write(self):
        with tempfile.TemporaryDirectory() as td:
            old_dir, old_current = bridge.DATA_DIR, bridge.CURRENT
            try:
                bridge.DATA_DIR = Path(td)
                bridge.CURRENT = Path(td) / "current.json"
                bridge.CURRENT.write_text('{"old": true}\n', encoding="utf-8")
                bridge.atomic_write({"schema": 1, "posts": [{"title": "new"}]})
                result = json.loads(bridge.CURRENT.read_text(encoding="utf-8"))
                self.assertEqual(result["posts"][0]["title"], "new")
            finally:
                bridge.DATA_DIR, bridge.CURRENT = old_dir, old_current

    def test_failed_fetch_does_not_call_atomic_write(self):
        with mock.patch.object(bridge, "fetch_feed", side_effect=ValueError("bad feed")), \
             mock.patch.object(bridge, "atomic_write") as writer, \
             mock.patch.dict("os.environ", {"SFANDOM_BLOGGER_FEED": "https://example.blogspot.com/feeds/posts/default"}):
            code = bridge.main()
            self.assertEqual(code, 1)
            writer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
