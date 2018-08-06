"""
Retrieve books on a GoodReads user's "shelf."

Author: David Cain

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from collections import namedtuple
import logging
import re

import requests
import urllib.parse as urlparse
from bs4 import BeautifulSoup


logger = logging.getLogger('bibliophile')


Book = namedtuple('Book', ['isbn', 'title', 'author', 'description', 'image_url'])


# Expect image urls to conform to a certain scheme
goodreads_image_regex = re.compile(
    r'^/books/'
    r'(?P<slug>\d*)(?P<size>[sml])/'  # size: 'small', 'medium', or 'large'
    r'(?P<isbn>\d*).jpg$'
)


def higher_quality_cover(image_url):
    """ Modify a book cover to be higher quality. """
    parsed = urlparse.urlparse(image_url)
    match = goodreads_image_regex.match(parsed.path)
    if not match:
        logger.warning("Goodreads image format changed! (%s)"
                       "Returning original quality image.", parsed.path)
        return image_url
    larger_path = f"/books/{match.group('slug')}l/{match.group('isbn')}.jpg"
    return parsed._replace(path=larger_path).geturl()


class ShelfReader:
    """ Read books from a given user's Goodreads shelves. """

    def __init__(self, user_id, dev_key):
        self.user_id = user_id
        self.dev_key = dev_key

    @staticmethod
    def get(path, params):
        """ Return BS tag for the response to a given Goodreads API route. """
        endpoint = urlparse.urljoin('https://www.goodreads.com/', path)
        resp = requests.get(endpoint, params=params)
        return BeautifulSoup(resp.content, 'xml').find('GoodreadsResponse')

    def wanted_books(self, shelf):
        """ All books that the user wants to read. """
        # See: https://www.goodreads.com/api/index#reviews.list
        logger.info("Fetch books on %s for user %s", shelf, self.user_id)
        body = self.get('review/list', {
            'v': 2,
            'id': self.user_id,
            'shelf': shelf,
            'key': self.dev_key,
            'per_page': 200,  # TODO: Paginate if more than 200 books.
        })

        for review in body.find('reviews').findAll('review'):
            yield Book(
                isbn=review.isbn.text,  # Can be blank! e.g. in e-Books
                title=review.title.text,
                author=review.author.find('name').text,
                description=review.description.text,
                image_url=higher_quality_cover(review.image_url.text)
            )
