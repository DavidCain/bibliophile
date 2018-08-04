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
import csv
import logging
import os
import sys

from bibliophile.goodreads import ShelfReader
from bibliophile.bibliocommons import BiblioParser


logger = logging.getLogger('bibliophile')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(ch)


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
