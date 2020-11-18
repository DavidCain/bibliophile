""" Tests the lambda function which hits the BiblioCommons API. """
import json
import unittest
from unittest import mock

from aws_lambda_context import LambdaContext

from bibliophile.bibliocommons import parse
from bibliophile.bibliocommons.types import Book, BookDescription

from ..search_catalog import handler

dummy_context = LambdaContext()


class HandlerTest(unittest.TestCase):
    """ Test the lambda function handler which queries the catalog. """

    def test_null_body(self):
        """ If there is no POST data at all, we handle that. """
        response = handler({'body': None}, context=dummy_context)
        self.assertEqual(
            response,
            {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': "No data given!",
            },
        )

    def test_no_body(self):
        """ If the endpoint gets an empty payload, we handle that. """
        response = handler({'body': '{}'}, context=dummy_context)
        self.assertEqual(
            response,
            {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': "No body given!",
            },
        )

    def test_no_books(self):
        """ Books must be given in a complete list. """
        no_books = {
            'books': [],
            'biblio_subdomain': 'seattle',
            'branch': 'Ballard Branch',
        }
        response = handler({'body': json.dumps(no_books)}, context=dummy_context)
        self.assertEqual(
            response,
            {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': "Specify books in a structured list!",
            },
        )

    def test_malformed_books(self):
        """ Books must be given as structured data. """
        no_books = {
            'books': ["Harry Potter"],
            'biblio_subdomain': 'seattle',
            'branch': 'Ballard Branch',
        }
        response = handler({'body': json.dumps(no_books)}, context=dummy_context)
        self.assertEqual(
            response,
            {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': "Specify books in a structured list!",
            },
        )

    def test_incorrect_fields(self):
        """ Books must be structured correctly. """
        no_books = {
            'books': [{'name': "Harry Potter"}],
            'biblio_subdomain': 'seattle',
            'branch': 'Ballard Branch',
        }
        response = handler({'body': json.dumps(no_books)}, context=dummy_context)
        self.assertEqual(
            response,
            {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': "Books must include fields ('isbn', 'title', 'author')",
            },
        )

    def test_missing_fields(self):
        """ Books must be structured with all required fields. """
        no_books = {
            'books': [{'title': "Harry Potter"}],
            'biblio_subdomain': 'seattle',
            'branch': 'Ballard Branch',
        }
        response = handler({'body': json.dumps(no_books)}, context=dummy_context)
        self.assertEqual(
            response,
            {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': "Books must include fields ('isbn', 'title', 'author')",
            },
        )

    def test_string_arg_missing(self):
        """ We warn if a required arg is missing. """
        body = {'branch': 'sfpl', 'biblio_subdomain': ''}
        response = handler({'body': json.dumps(body)}, context=dummy_context)
        self.assertEqual(
            response,
            {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': "Missing value for biblio_subdomain",
            },
        )

    def test_success(self):
        """ We search for all specified books. """
        okay_payload = {
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

        fake_parser = mock.Mock(spec=parse.BiblioParser)
        fake_parser.all_matching_books.return_value = iter(
            [
                Book(
                    title="Cat's Cradle",
                    author='Kurt Vonnegut Jr.',
                    description='and the silver spoon...',
                    call_number='F VONNEGUT',
                    cover_image='https://secure.syndetics.com/index.aspx?isbn=9780385333481/MC.GIF&client=sfpl&type=xw12&oclc=',
                    full_record_link='https://sfpl.bibliocommons.com/item/show/1268424093',
                ),
            ]
        )

        with mock.patch.dict('os.environ', {'GOODREADS_DEV_KEY': 'fake-key'}):
            # pylint: disable=invalid-name
            with mock.patch.object(parse, 'BiblioParser') as BiblioParser:
                BiblioParser.return_value = fake_parser

                response = handler(
                    {'body': json.dumps(okay_payload)}, context=dummy_context
                )

        BiblioParser.assert_called_once_with(
            biblio_subdomain='sfpl', branch='MAIN', isolanguage='eng'
        )
        fake_parser.all_matching_books.assert_called_once_with(
            [
                BookDescription(
                    isbn='0140285601',
                    title="Cat's Cradle",
                    author='Kurt Vonnegut Jr.',
                )
            ]
        )

        self.assertEqual(
            response,
            {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Credentials': True,
                },
                'body': (
                    '{"books": [{'
                    '"title": "Cat\'s Cradle", '
                    '"author": "Kurt Vonnegut Jr.", '
                    '"description": "and the silver spoon...", '
                    '"call_number": "F VONNEGUT", '
                    '"cover_image": "https://secure.syndetics.com/index.aspx?isbn=9780385333481/MC.GIF&client=sfpl&type=xw12&oclc=", '
                    '"full_record_link": "https://sfpl.bibliocommons.com/item/show/1268424093"}'
                    ']}'
                ),
            },
        )
