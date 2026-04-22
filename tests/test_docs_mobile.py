import unittest
from pathlib import Path


class TestDocsMobileUX(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path("docs/index.html").read_text(encoding="utf-8")

    def test_results_table_uses_horizontal_scroll_wrapper(self):
        self.assertIn('.table-scroll {', self.html)
        self.assertRegex(
            self.html,
            r'<div class="table-scroll">\s*<table class="results-table">',
        )

    def test_zoomable_sections_exist_for_large_images(self):
        self.assertGreaterEqual(self.html.count('class="zoomable-media"'), 2)
        self.assertIn('id="media-lightbox"', self.html)
        self.assertIn("document.querySelectorAll('.zoomable-media')", self.html)

    def test_field_footage_uses_responsive_classes_not_fixed_heights(self):
        self.assertIn('class="field-clips-grid"', self.html)
        self.assertIn('class="field-compare-grid"', self.html)
        self.assertIn('.field-video {', self.html)
        self.assertNotIn('height:280px', self.html)
        self.assertNotIn('height:320px', self.html)


if __name__ == '__main__':
    unittest.main()
