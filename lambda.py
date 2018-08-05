#!/usr/bin/env python3

"""
Use AWS Lambda to find books you want to read at your local library.

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

import json
import os

from bibliophile.goodreads import ShelfReader
from bibliophile.bibliocommons import BiblioParser


GOODREADS_DEV_KEY = os.environ['GOODREADS_DEV_KEY']


def error(message):
    return {
        'statusCode': 400,
        'headers': {'Content-Type': 'application/json'},
        'body': message
    }


def handler(event, context):
    body = json.loads(event.get('body', '{}'))

    shelf = body.get('shelf', 'to-read')
    biblio = body.get('biblio', 'sfpl')
    branch = body.get('branch', 'MAIN')

    try:
        reader = ShelfReader(body['userId'], GOODREADS_DEV_KEY)
    except KeyError:
        return error("No user id supplied!")
    except Exception as e:
        return error("Something went wrong.")

    wanted_books = list(reader.wanted_books(shelf))
    books = [bk._asdict() for bk in BiblioParser(wanted_books, branch, biblio)]

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
        },
        'body': json.dumps({'books': books})
    }


if __name__ == '__main__':
    body = {'userId': os.environ['GOODREADS_USER_ID']}

    print(handler({'body': json.dumps(body)}, None))
