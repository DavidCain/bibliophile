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
from collections import namedtuple
import logging
import html
import csv
import os
import sys

import grequests
import requests
import urllib.parse as urlparse
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(ch)


def grouper(input_list, chunk_size):
    for i in range(0, len(input_list), chunk_size):
        yield input_list[i: i + chunk_size]


class UnstableAPIError(RuntimeError):
    """ Indicates a failed assumption about an unstable API. """
    pass


Book = namedtuple('Book', ['isbn', 'title', 'author'])


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
                author=review.author.find('name').text
            )


class BiblioParser:
    """ Use undocumented BiblioCommons APIs to extract book information. """
    def __init__(self, books, branch=None, biblio_subdomain='seattle'):
        self.books = books
        self.branch = branch
        self.root = f'https://{biblio_subdomain}.bibliocommons.com/'

    @staticmethod
    def single_query(book, print_only=True):
        """ Get query for one book - Use its ISBN (preferred) or title + author. """
        conditions = {}

        if book.isbn:
            conditions['identifier'] = book.isbn
        else:
            conditions['contributor'] = book.author
            conditions['title'] = book.title
            if print_only:
                conditions['formatcode'] = 'BK'

        rules = [f'{name}:({val})' for name, val in conditions.items()]
        query = ' AND '.join(rules)
        return f'({query})' if len(rules) > 1 else query

    @classmethod
    def bibliocommons_query(cls, books, branch):
        """ Get query for "any of these books available at this branch."

        This query can be used in any Bibliocommons-driven catalog.
        """
        isbn_match = ' OR '.join(cls.single_query(book) for book in books)
        query = f'({isbn_match}) available:"{branch}"' if branch else isbn_match

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

    def async_record(self, title, rss_link):
        """ Return an asynchronous request for info about the given book.

        The response content will be the "full record," containing information
        about the given title.
        """
        path = 'item/full_record/{}'.format(self.extract_item_id(rss_link))
        url = urlparse.urljoin(self.root, path)

        def attach_title(response, **kwargs):
            """ Store the book title as metadata on the response object. """
            response._title = title
            return response

        return grequests.get(url, hooks={'response': attach_title})

    def async_book_lookup(self, query):
        """ Formulate & return a request that executes the query.

        The object can be asynchronously queried in a bunch with grequests.
        """
        # BiblioCommons only opens up their API to library employees
        # As of 2011, they said it would publicly-available 'soon'... =(
        rss_search = urlparse.urljoin(self.root, 'search/rss')
        params = {'custom_query': query}

        # grequests doesn't store the (full) url on AsyncRequest objects
        full_url = f"{rss_search}?{urlparse.urlencode(params)}"
        logger.debug("Searching books via RSS: '%s'", full_url)

        return grequests.get(rss_search, params=params)

    def matching_books(self, query_response):
        """ Yield descriptors of all books matched by the query. """
        soup = BeautifulSoup(query_response.content, 'xml')
        matches = soup.find('channel').findAll('item')

        for match in matches:
            title = html.unescape(match.title.text)
            desc_soup = BeautifulSoup(match.description.text, 'html.parser')
            label = desc_soup.find(text='Call #:')  # It's a `<b>` tag
            call_num = label.next_element.strip() if label else None
            yield title, match.link.text, call_num

    def get_call_number(self, full_record_response):
        """ Extract a book's call number from its catalog query response. """
        # Yes, that's a JSON endpont that returns HTML. ಠ_ಠ
        soup = BeautifulSoup(full_record_response.json()['html'], 'html.parser')
        call_num = soup.find(testid="callnum_branch").find('span', class_='value')
        return call_num.text

    def catalog_results(self):
        """ Yield all books found in the catalog, in no particular order. """
        # Undocumented, but the API appears to only support lookup of 10 books
        queries = (self.bibliocommons_query(isbn_chunk, self.branch)
                   for isbn_chunk in grouper(self.books, 10))
        lookup_requests = [self.async_book_lookup(q) for q in queries]
        for response in grequests.imap(lookup_requests):
            for book in self.matching_books(response):
                yield book

    def __iter__(self):
        """ Yield all matching books for the supplied books & branch. """
        search = "Searching library catalog for books"
        if self.branch:
            search += f" at {self.branch}"
        logger.info(search)

        full_record_requests = []

        for title, link, call_num in self.catalog_results():
            if call_num:
                yield title, call_num
            else:
                logger.debug("No call # found for %s, fetching record.", title)
                full_record_requests.append(self.async_record(title, link))

        for response in grequests.imap(full_record_requests):
            call_num = self.get_call_number(response)
            response.close()
            yield (response._title, call_num)


def find_books(user_id, dev_key, shelf, branch, biblio, csvname=None):
    """ Print books to stdout, optionally export to csvname. """
    reader = ShelfReader(user_id, dev_key)
    wanted_books = list(reader.wanted_books(shelf))
    logger.info("%d books found on shelf", len(wanted_books))
    writer = None
    if csvname:
        csvfile = open(csvname, 'w')
        writer = csv.writer(csvfile)
        writer.writerow(["Title", "Call Number"])
    for title, call_num in BiblioParser(wanted_books, branch, biblio):
        logger.info("  %s - %s", title, call_num)
        if writer:
            writer.writerow([title, call_num])
    if writer:
        csvfile.close()
        logger.info("Available books written to %s", csvfile.name)


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
