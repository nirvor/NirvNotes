import unittest

from notes.file_system.file_system import FileSystemNotes


class HtmlTagExtractionTests(unittest.TestCase):
    def test_inline_hashtag_mentions_are_not_html_tags(self):
        content = """<!doctype html>
<html>
  <head><meta name="flatnotes-tags" content="infra,research"></head>
  <body>
    <article>
      <h1>System tags</h1>
      <p>Users do not need to type #pinned in normal prose.</p>
      <p>#infra #research</p>
    </article>
  </body>
</html>
"""

        _, tags = FileSystemNotes._extract_tags(content)

        self.assertEqual(tags, {"infra", "research"})

    def test_legacy_tag_only_html_blocks_remain_supported(self):
        content = """<article>
  <h1>Legacy note</h1>
  <p>#private #pinned</p>
</article>"""

        _, tags = FileSystemNotes._extract_tags(content)

        self.assertEqual(tags, {"private", "pinned"})

    def test_pinned_metadata_remains_a_system_tag(self):
        content = """<html>
  <head><meta name="flatnotes-tags" content="private,pinned"></head>
  <body><p>Normal text mentioning #other.</p></body>
</html>"""

        _, tags = FileSystemNotes._extract_tags(content)

        self.assertEqual(tags, {"private", "pinned"})


if __name__ == "__main__":
    unittest.main()
