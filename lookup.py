#!/usr/bin/env python3

"""
See which books you want to read are available at your local library.

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

import argparse
import html
import csv
import os

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
    """ Use undocumented BiblioCommons APIs to extract book information. """
    def __init__(self, isbns, branch=None, biblio_subdomain='seattle'):
        self.isbns = isbns
        self.branch = branch
        self.root = 'https://{}.bibliocommons.com/'.format(biblio_subdomain)

    @staticmethod
    def bibliocommons_query(isbns, branch):
        """ Get query for "any of these ISBNS available at this branch."

        This query can be used in any Bibliocommons-driven catalog.
        """
        isbn_match = ' OR '.join('identifier:({})'.format(isbn) for isbn in isbns)
        if branch:
            query = '({}) available:"{}"'.format(isbn_match, branch)
        else:
            query = isbn_match

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

    def get_call_number(self, rss_link):
        """ Get a book's call number from its link in the catalog. """

        path = 'item/full_record/{}'.format(self.extract_item_id(rss_link))
        url = urlparse.urljoin(self.root, path)

        # A JSON endpont that returns HTML. ಠ_ಠ
        html = requests.get(url).json()['html']
        soup = BeautifulSoup(html, 'html.parser')
        call_num = soup.find(testid="callnum_branch").find('span', class_='value')
        return call_num.text

    def matching_books(self, query):
        """ Yield title and call number of all available books. """
        # BiblioCommons only opens up their API to library employees
        # As of 2011, they said it would publicly-available 'soon'... =(
        rss_search = urlparse.urljoin(self.root, 'search/rss')
        resp = requests.get(rss_search, params={'custom_query': query})
        soup = BeautifulSoup(resp.content, 'xml')
        matches = soup.find('channel').findAll('item')
        for match in matches:
            title = html.unescape(match.title.text)
            call_num = self.get_call_number(match.link.text)
            yield (title, call_num)

    def __iter__(self):
        """ Yield all matching books for the supplied ISBNs & branch. """
        # Undocumented, but the API appears to only support lookup of 10 books
        for isbn_chunk in grouper(self.isbns, 10):
            query = self.bibliocommons_query(isbn_chunk, self.branch)
            for match in self.matching_books(query):
                yield match


def find_books(user_id, dev_key, shelf, branch, biblio, csvname=None):
    """ Print books to stdout, optionally export to csvname. """
    reader = ShelfReader(user_id, dev_key)
    isbns = [book['ISBN'] for book in reader.wanted_books(shelf)]
    writer = None
    if csvname:
        csvfile = open(csvname, 'w')
        writer = csv.writer(csvfile)
        writer.writerow(["Title", "Call Number"])
    for title, call_num in BiblioParser(isbns, branch, biblio):
        print("{} - {}".format(title, call_num))
        if writer:
            writer.writerow([title, call_num])
    if writer:
        csvfile.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="See which books you want to read are available at your local library."
    )
    parser.add_argument(
        'user_id', type=int,
        nargs='?', default=os.environ.get('GOODREADS_USER_ID'),
        help="User's ID on Goodreads"
    )
    parser.add_argument(
        'dev_key',
        nargs='?', default=os.environ.get('GOODREADS_DEV_KEY'),
        help="Goodreads developer key. See https://www.goodreads.com/api"
    )
    parser.add_argument(
        '--branch', default=None,
        help="Only show titles available at this branch. e.g. 'Fremont Branch'"
    )
    parser.add_argument(
        '--shelf', default='to-read',
        help="Name of the shelf containing desired books"
    )
    parser.add_argument(
        '--biblio', default='seattle',
        help="subdomain of bibliocommons.com (seattle, vpl, etc.)"
    )
    parser.add_argument(
        '--csv', default=None,
        help="Output results to a CSV of this name."
    )

    args = parser.parse_args()
    if not args.user_id:
        parser.error("Pass user_id positionally, or set GOODREADS_USER_ID")
    if not args.dev_key:
        parser.error("Pass dev_key positionally, or set GOODREADS_DEV_KEY")
    find_books(args.user_id, args.dev_key, args.shelf, args.branch,
               args.biblio, args.csv)
