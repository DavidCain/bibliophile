import unittest

from ..goodreads import higher_quality_cover


class CoverImageTests(unittest.TestCase):
    def test_nophoto_url_unchanged(self):
        """ We handle Goodreads' "nophoto" URL. """
        nophoto = ("https://www.goodreads.com/"
                   "assets/nophoto/book/111x148-bcc042a9c91a29c1d680899eff700a03.png")
        image_url = higher_quality_cover(nophoto)
        self.assertEqual(image_url, nophoto)

    def test_medium_photo_enlarged(self):
        """ We can produce higher-quality images for medium-sized cover. """
        self.assertEqual(
            higher_quality_cover('https://images.gr-assets.com/books/1436292289m/25663961.jpg'),
            'https://images.gr-assets.com/books/1436292289l/25663961.jpg'
        )

    def test_small_photo_enlarged(self):
        """ We can produce higher-quality images for a small-sized cover. """
        self.assertEqual(
            higher_quality_cover('https://images.gr-assets.com/books/1550917827s/1202.jpg'),
            'https://images.gr-assets.com/books/1550917827l/1202.jpg'
        )
