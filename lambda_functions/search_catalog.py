#!/usr/bin/env python3

"""
Use AWS Lambda to search for books in a library catalog.
"""
import json
from typing import Any, Dict, Iterator, List, Optional

from aws_lambda_context import LambdaContext

from bibliophile.bibliocommons import parse
from bibliophile.bibliocommons.types import Book, BookDescription

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
    """Bulk search for books in the BiblioCommons catalog.

    Event body should look like:

        {
            'biblio_subdomain': 'sfpl',
            'branch': 'MAIN',
            'books': [
                {
                    'isbn': '0140285601',
                    'title': "Cat's Cradle",
                    'author': 'Kurt Vonnegut Jr.',
                }
            ],
        }
    """
    json_body: Optional[str] = event.get('body', '{}')
    if json_body is None:
        return error("No data given!")

    body: JsonDict = json.loads(json_body)
    if not body:
        return error("No body given!")

    str_args = ('biblio_subdomain', 'branch')
    missing_values = [name for name in str_args if not body.get(name)]
    if missing_values:
        return error(f"Missing value for {', '.join(missing_values)}")

    biblio_subdomain: str = body['biblio_subdomain']
    branch: str = body['branch']
    isolanguage: str = body.get('isolanguage', 'eng')

    dict_books: List[JsonDict] = body.get('books', [])
    if not (
        dict_books
        and isinstance(dict_books, list)
        and all(isinstance(dict_book, dict) for dict_book in dict_books)
    ):
        return error("Specify books in a structured list!")

    try:
        descriptions: List[BookDescription] = [
            BookDescription(**book_dict) for book_dict in dict_books
        ]
    except (KeyError, TypeError):
        return error(f"Books must include fields {BookDescription._fields}")

    biblio_parser = parse.BiblioParser(
        biblio_subdomain=biblio_subdomain,
        branch=branch,
        isolanguage=isolanguage,
    )
    books: Iterator[Book] = biblio_parser.all_matching_books(descriptions)

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
        'body': json.dumps({'books': [book._asdict() for book in books]}),
    }
