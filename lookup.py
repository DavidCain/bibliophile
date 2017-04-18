#!/usr/bin/env python3

import argparse

import requests
import urllib.parse as urlparse
from bs4 import BeautifulSoup


class ShelfReader:
    """ Read books from a given user's Goodreads shelves. """

    def __init__(self, user_id, dev_key):
        self.user_id = user_id
        self.dev_key = dev_key

    def get(self, path, params):
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
                'title': review.title.text,
                'author': review.author.find('name').text
            }
            yield book


def find_books(user_id, dev_key, shelf):
    reader = ShelfReader(user_id, dev_key)
    for book in reader.wanted_books(shelf):
        # TODO: Actually query local library
        print("{} - {}".format(book['title'], book['author']))


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
    find_books(args.user_id, args.dev_key, args.shelf)
