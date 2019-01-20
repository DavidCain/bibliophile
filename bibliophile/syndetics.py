import urllib.parse as urlparse


def higher_quality_cover(image_url):
    """ Modify a book cover request to be higher quality.

    By default, the BiblioCommons  catalog shows medium-quality images (GIF,
    187x187). There are higher-quality images available though (JPG, 400x400).

    This method returns a new URL that requests the same resource from the
    Syndetics catalog, but in higher quality. The other querystring parameters,
    such as those identifying the client or making requests for certain
    metadata, are left unmodified.

    Documentation on the URL scheme can be found in the 'Syndetics Starter Page':
    https://developers.exlibrisgroup.com/resources/voyager/code_contributions/SyndeticsStarterDocument.pdf
    """
    parsed = urlparse.urlparse(image_url)
    params = urlparse.parse_qs(parsed.query)
    if 'isbn' not in params:
        # We might receive a placeholder image, use that instead
        return image_url

    isbn, filename = params['isbn'][0].split('/')  # '123456789/SC.GIF'
    params['isbn'] = f"{isbn}/LC.jpg"  # (higher quality image)
    large_cover = parsed._replace(query=urlparse.urlencode(params, doseq=True))
    return large_cover.geturl()
