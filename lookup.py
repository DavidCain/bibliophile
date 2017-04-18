#!/usr/bin/env python3

import argparse
import html

import requests
import urllib.parse as urlparse
from bs4 import BeautifulSoup


def grouper(input_list, chunk_size):
    for i in range(0, len(input_list), chunk_size):
        yield input_list[i: i + chunk_size]


class UnstableAPIError(RuntimeError):
    """ Indicates a failed assumption about an unstable API. """
    pass


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
        body = self.get('review/list', {
            'v': 2,
            'id': self.user_id,
            'shelf': shelf,
            'key': self.dev_key,
            'per_page': 200,  # TODO: Paginate if more than 200 books.
        })

        for review in body.find('reviews').findAll('review'):
            book = {
                'ISBN': review.isbn.text,
                'title': review.title.text,
                'author': review.author.find('name').text
            }
            yield book


class BiblioParser:
    lib_root = 'https://seattle.bibliocommons.com/'
    """ Use undocumented BiblioCommons APIs to extract book information. """
    def __init__(self, isbns, branch):
        self.isbns = isbns
        self.branch = branch

    @staticmethod
    def bibliocommons_query(isbns, branch):
        """ Get query for "any of these ISBNS available at this branch."

        This query can be used in any Bibliocommons-driven catalog.
        """
        isbn_match = ' OR '.join('identifier:({})'.format(isbn) for isbn in isbns)
        query = '({}) available:"{}"'.format(isbn_match, branch)
        if len(query) > 900:
            # Shouldn't happen in practice, since we group queries
            raise ValueError("BiblioCommons queries are limited to 900 chars!")
        return query

    @staticmethod
    def extract_item_id(rss_link):
        """ Extract a numeric ID from a link to a book summary.

        seattle.bibliocommons.com/item/show/2837203030_moby_dick -> 2837203030

        The RSS feed for a given search links to a page with information about
        that book. The URL is a slug containing an item ID. We need that ID to
        form other requests.
        """
        path = urlparse.urlsplit(rss_link).path
        if not path.startswith('/item/show/'):
            raise UnstableAPIError("RSS link format changed!")

        slug = path.split('/')[-1]  # '2837203030_moby_dick'
        item_id = slug.split('_')[0]  # '2837203030'
        if not item_id.isdigit():
            raise UnstableAPIError("slug format changed!")
        return int(item_id)

    @classmethod
    def get_call_number(cls, rss_link):
        """ Get a book's call number from its link in the catalog. """

        path = 'item/full_record/{}'.format(cls.extract_item_id(rss_link))
        url = urlparse.urljoin(cls.lib_root, path)

        # A JSON endpont that returns HTML. ಠ_ಠ
        html = requests.get(url).json()['html']
        soup = BeautifulSoup(html, 'html.parser')
        call_num = soup.find(testid="callnum_branch").find('span', class_='value')
        return call_num.text

    @classmethod
    def matching_books(cls, query):
        """ Yield title and call number of all available books. """
        # BiblioCommons only opens up their API to library employees
        # As of 2011, they said it would publicly-available 'soon'... =(
        rss_search = urlparse.urljoin(cls.lib_root, 'search/rss')
        resp = requests.get(rss_search, params={'custom_query': query})
        soup = BeautifulSoup(resp.content, 'xml')
        matches = soup.find('channel').findAll('item')
        for match in matches:
            title = html.unescape(match.title.text)
            call_num = cls.get_call_number(match.link.text)
            yield (title, call_num)

    def __iter__(self):
        """ Yield all matching books for the supplied ISBNs & branch. """
        # Undocumented, but the API appears to only support lookup of 10 books
        for isbn_chunk in grouper(self.isbns, 10):
            query = self.bibliocommons_query(isbn_chunk, self.branch)
            for match in self.matching_books(query):
                yield match


def find_books(user_id, dev_key, shelf, branch):
    reader = ShelfReader(user_id, dev_key)
    isbns = [book['ISBN'] for book in reader.wanted_books(shelf)]
    for book in BiblioParser(isbns, branch):
        print(book)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="See which books you want to read are available at your local library."
    )
    parser.add_argument(
        'user_id', type=int,
        help="User's ID on Goodreads"
    )
    parser.add_argument(
        'dev_key',
        help="Goodreads developer key. See https://www.goodreads.com/api"
    )
    parser.add_argument(
        '--branch', default='Fremont Branch',
        help="Only show titles available at this branch. e.g. 'Fremont Branch'"
    )
    parser.add_argument(
        '--shelf', default='to-read',
        help="Name of the shelf containing desired books"
    )

    args = parser.parse_args()
    find_books(args.user_id, args.dev_key, args.shelf, args.branch)
