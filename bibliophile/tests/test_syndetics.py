import unittest

from ..syndetics import higher_quality_cover


class SyndeticsTest(unittest.TestCase):
    def test_unrecognize_images_returned_as_is(self):
        """ If there's no ISBN in the URL, we don't modify the URL. """
        img_url = 'https://secure.syndetics.com/index.aspx?fake_url'
        self.assertEqual(higher_quality_cover(img_url), img_url)

    def test_small_gif_becomes_large_jpeg(self):
        """ We transform small images to larger ones. """
        base_url = 'https://secure.syndetics.com/index.aspx'
        self.assertEqual(
            higher_quality_cover(
                f'{base_url}?isbn=9780140449266/SC.GIF&client=sfpl&type=xw12&oclc='
            ),
            f'{base_url}?isbn=9780140449266%2FLC.jpg&client=sfpl&type=xw12'
        )
