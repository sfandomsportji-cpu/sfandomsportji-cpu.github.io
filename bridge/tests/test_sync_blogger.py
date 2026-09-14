import importlib.util, json, tempfile, unittest
from pathlib import Path
from unittest import mock

MODULE_PATH=Path(__file__).resolve().parents[1]/'sync_blogger.py'
spec=importlib.util.spec_from_file_location('sync_blogger',MODULE_PATH); bridge=importlib.util.module_from_spec(spec); spec.loader.exec_module(bridge)
VALID_ATOM=b'''<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>SFANDOM TEST</title><entry><id>tag:blogger.com,1999:blog-1.post-9</id><title>Safe Test Post</title><published>2026-09-15T00:10:00+09:00</published><updated>2026-09-15T00:11:00+09:00</updated><link rel="alternate" href="https://example.blogspot.com/2026/09/test.html"/><category term="SFANDOM-SYNC"/><category term="MLB"/><content type="html">&lt;section class="hero"&gt;&lt;h2&gt;Hello&lt;/h2&gt;&lt;p onclick="bad()"&gt;World&lt;/p&gt;&lt;script&gt;bad()&lt;/script&gt;&lt;img src="https://blogger.googleusercontent.com/img/test.jpg" onerror="bad()"&gt;&lt;/section&gt;</content></entry></feed>'''
VALID_RSS=b'''<?xml version="1.0"?><rss version="2.0"><channel><item><guid>rss-1</guid><title>RSS Test</title><link>https://example.blogspot.com/2026/09/rss.html</link><pubDate>Mon, 14 Sep 2026 10:00:00 GMT</pubDate><category>SFANDOM-SYNC</category><description>&lt;b&gt;Safe text&lt;/b&gt;</description></item></channel></rss>'''
class BridgeSafetyTests(unittest.TestCase):
    def test_atom_sanitizes_active_content(self):
        posts=bridge.parse_feed(VALID_ATOM); posts=bridge.filter_required_label(posts,'SFANDOM-SYNC'); bridge.validate(posts)
        body=posts[0]['body_html'].lower(); self.assertIn('<h2>hello</h2>',body); self.assertNotIn('<script',body); self.assertNotIn('onclick',body); self.assertNotIn('onerror',body); self.assertIn('loading="lazy"',body)
    def test_valid_rss(self):
        posts=bridge.filter_required_label(bridge.parse_feed(VALID_RSS),'SFANDOM-SYNC'); bridge.validate(posts); self.assertEqual(posts[0]['summary'],'Safe text')
    def test_malformed_xml_rejected(self):
        with self.assertRaises(ValueError): bridge.parse_feed(b'<feed><entry>')
    def test_empty_feed_rejected(self):
        with self.assertRaises(ValueError): bridge.parse_feed(b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>''')
    def test_javascript_url_rejected(self): self.assertIsNone(bridge.safe_url('javascript:alert(1)'))
    def test_label_gate(self):
        posts=bridge.parse_feed(VALID_ATOM)
        with self.assertRaises(ValueError): bridge.filter_required_label(posts,'NOT-PRESENT')
    def test_atomic_write(self):
        with tempfile.TemporaryDirectory() as td:
            old_dir,old_cur=bridge.DATA_DIR,bridge.CURRENT
            try:
                bridge.DATA_DIR=Path(td); bridge.CURRENT=Path(td)/'current.json'; bridge.CURRENT.write_text('{"old":true}\n')
                bridge.atomic_write({'schema':2,'posts':[{'title':'new'}]}); self.assertEqual(json.loads(bridge.CURRENT.read_text())['posts'][0]['title'],'new')
            finally: bridge.DATA_DIR,bridge.CURRENT=old_dir,old_cur
    def test_failed_fetch_does_not_write(self):
        with mock.patch.object(bridge,'fetch_feed',side_effect=ValueError('bad feed')), mock.patch.object(bridge,'atomic_write') as writer, mock.patch.dict('os.environ',{'SFANDOM_BLOGGER_FEED':'https://example.blogspot.com/feeds/posts/default','SFANDOM_REQUIRED_LABEL':'SFANDOM-SYNC'}):
            self.assertEqual(bridge.main(),1); writer.assert_not_called()
    def test_missing_feed_is_safe_noop(self):
        with mock.patch.dict('os.environ',{},clear=True): self.assertEqual(bridge.main(),0)
if __name__=='__main__': unittest.main()
