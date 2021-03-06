#!/usr/bin/env python3

"""
Use AWS Lambda to extract books from a user's Goodreads shelf.
"""
# Bibliophile's import monkey-patches SSL via a `grequests` import
# It's important that this happen *before* boto3 imports SSL
# We can remove this once migrating away from grequests
import bibliophile  # isort: skip, pylint: disable=unused-import

import json
import os
import time
import typing
from datetime import timedelta
from typing import Any, Dict, List, Optional, Type, TypeVar

import boto3
from aws_lambda_context import LambdaContext

from bibliophile import goodreads
from bibliophile.goodreads.types import Book

JsonDict = Dict[str, Any]


# The Goodreads API terms request that we not cache information longer than 24 hours
GOODREADS_CACHE_DURATION = int(timedelta(hours=24).total_seconds())


# Make a generic type for use in annotating classmethod factory for mypy
T = TypeVar('T', bound='ShelfResult')  # pylint: disable=invalid-name


class ShelfResult(typing.NamedTuple):
    """ Wrap the results of a "read shelf" operation to indicate cache hit/miss. """

    books: List[Book]

    # If null, these results were freshly obtained.
    # Otherwise, the timestamp at which we last read the shelf for the user
    retrieved_timestamp: Optional[int]

    @property
    def is_cached(self) -> bool:
        """ Did this result get read from the cache? """
        return self.retrieved_timestamp is not None

    # NOTE: In Python 3.8 we can use `postponed evaluations of annotations`
    # to just have this method return ShelfResult
    @classmethod
    def from_cached_item(cls: Type[T], item: JsonDict) -> T:
        """ Build a result from a cached value in DynamoDB. """
        return cls(
            # Note that this constructor relies on Book having primitive types...
            # (If Book had other NamedTuples for instance, this would not work)
            books=[Book(**bk_dict) for bk_dict in item['books']],
            # Coerce this timestamp to an int, since it comes back as a Decimal
            retrieved_timestamp=int(item['retrievedTimestamp']),
        )


def get_wanted_books(user_id: str, shelf: str, skip_cache: bool = False) -> ShelfResult:
    """Get books on the user's shelf, using cache if available.

    Reading from a user's Goodreads shelf is an expensive operation.
    We shouldn't hit the endpoint more than once per second, and it takes
    approximately 5s to respond for a user with ~100 books on their shelf.

    Because shelves rarely change, we can rely on a cached version from
    the last 24 hours.
    """
    assert user_id
    now_ts = int(time.time())

    # When reading/writing from the cache, this is the key we'll use.
    key = f'{user_id}-{shelf}'
    pk_dict = {'userAndShelf': key}

    # For local testing, pass: region_name='localhost', endpoint_url='http://localhost:8000'
    # TODO (Set up integration tests)
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('shelvedBooks')

    # Try reading information from the cache first.
    if not skip_cache:
        cache = table.get_item(Key=pk_dict)
        if 'Item' in cache:  # Hit!
            return ShelfResult.from_cached_item(cache['Item'])

    # If the cache missed, then fetch the shelf now (should take ~5s)
    # (Raises ValueError on key missing)
    reader = goodreads.ShelfReader(user_id, os.environ['GOODREADS_DEV_KEY'])
    wanted_books = list(reader.wanted_books(shelf))

    table.get_item(Key={'userAndShelf': key})

    # Write to the cache now so reads are faster next time.
    table.put_item(
        Item={
            **pk_dict,
            'userId': user_id,
            'shelf': shelf,
            'retrievedTimestamp': now_ts,
            'ttl': now_ts + GOODREADS_CACHE_DURATION,
            # TODO (Python 3.7): `NamedTuple._as_dict()` doesn't work in a nested fashion.
            # If we used dataclasses instead, we could use the `as_dict()` method, which *does*
            'books': [bk._asdict() for bk in wanted_books],
        }
    )

    return ShelfResult(books=wanted_books, retrieved_timestamp=None)


def error(message: str) -> JsonDict:
    """ Return a simple error message in a Lambda-compatible dict. """
    return {
        'statusCode': 400,
        'headers': {'Content-Type': 'application/json'},
        'body': message,
    }


def handler(
    event: JsonDict, context: LambdaContext  # pylint: disable=unused-argument
) -> JsonDict:
    """ Read books from the user's shelf! """
    json_body: Optional[str] = event.get('body', '{}')
    if json_body is None:
        return error("No data given!")

    body: JsonDict = json.loads(json_body)
    if not body:
        return error("No body given!")

    # The shelf is expected, but most every user has the default 'to-read' shelf.
    shelf = body.get('shelf', 'to-read')

    user_id: Optional[str] = body.get('userId')
    if not user_id:
        return error("No user id supplied!")

    skip_cache: bool = body.get('skipCache', False)

    try:
        result = get_wanted_books(user_id, shelf, skip_cache=skip_cache)
    except ValueError:
        return error("Something went wrong.")  # Most likely bad dev key in env

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            # In order to call `api.dcain.me/<RouteName>` from origins other than
            # `api.dcain.me`, we must enable CORS.
            #
            # To enable CORS fully, the first step is to "Enable CORS" from within the
            # API Gateway console (or, preferably, by using `cors:true` in
            # `serverless.yml` for each function). This will automatically configure the
            # `OPTIONS` route with the appropriate CORS headers.
            #
            # The next step is to manually return CORS headers from the POST route.
            # (which is what the below headers do)
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
        },
        'body': json.dumps(
            {
                'isReadFromCache': result.is_cached,
                'cachedTimestamp': result.retrieved_timestamp,
                'books': [
                    {
                        'goodreads_id': book.goodreads_id,
                        'isbn': book.isbn,
                        'title': book.title,
                        'author': book.author,
                        # We also read the description + an image URL from Goodreads
                        # However, we avoid reporting that information since the description
                        # may come from Goodreads themselves, and we never hotlink images.
                    }
                    for book in result.books
                ],
            }
        ),
    }
