import unittest

from ..syndetics import higher_quality_cover


class SyndeticsTest(unittest.TestCase):
    def test_nophoto_url_unchanged(self):
        """ We handle Goodreads' "nophoto" URL. """
        nophoto = ("https://www.goodreads.com/"
                   "assets/nophoto/book/111x148-bcc042a9c91a29c1d680899eff700a03.png")
        image_url = higher_quality_cover(nophoto)
        self.assertEqual(image_url, nophoto)
