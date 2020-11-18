#!/usr/bin/env python3

"""
Use AWS Lambda to extract books from a user's Goodreads shelf.
"""
import json
import os
from typing import Any, Dict, Iterator, Optional

from aws_lambda_context import LambdaContext

from bibliophile import goodreads
from bibliophile.goodreads.types import Book

JsonDict = Dict[str, Any]


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

    try:
        reader = goodreads.ShelfReader(user_id, os.environ['GOODREADS_DEV_KEY'])
    except Exception:  # pylint: disable=broad-except
        return error("Something went wrong.")

    wanted_books: Iterator[Book] = reader.wanted_books(shelf)

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
        'body': json.dumps({'books': [bk._asdict() for bk in wanted_books]}),
    }
