""" Tests the lambda function which reads from Goodreads shelves. """
import json
import unittest
from unittest import mock

from aws_lambda_context import LambdaContext

from bibliophile import goodreads
from bibliophile.goodreads.types import Book

from ..read_shelf import handler

dummy_context = LambdaContext()


class HandlerTest(unittest.TestCase):
    """ Test the lambda function handler which reads from Goodreads shelves. """

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

    def test_no_user_id(self):
        """ The Goodreads user ID is required. """
        blank = handler({'body': '{"userId": null}'}, context=dummy_context)
        missing = handler({'body': '{"shelf": "to-read"}'}, context=dummy_context)

        for response in [blank, missing]:
            self.assertEqual(
                response,
                {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': "No user id supplied!",
                },
            )

    def test_missing_dev_key(self):
        """ We say something went wrong if dev key is missing. """
        with self.assertRaises(ValueError):
            goodreads.ShelfReader(user_id='123', dev_key='')

        okay_payload = {'userId': '12345', 'shelf': 'to-read'}
        with mock.patch.dict('os.environ', {'GOODREADS_DEV_KEY': ''}):
            response = handler(
                {'body': json.dumps(okay_payload)}, context=dummy_context
            )

        self.assertEqual(
            response,
            {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': "Something went wrong.",
            },
        )

    def test_success(self):
        """ An endpoint which provides a shelf & user ID returns books. """
        okay_payload = {'userId': '12345', 'shelf': 'custom-to-read'}

        fake_reader = mock.Mock(spec=goodreads.ShelfReader)
        fake_reader.wanted_books.return_value = [
            Book(
                goodreads_id="135479",
                isbn='0140285601',
                title="Cat's Cradle",
                author='Kurt Vonnegut Jr.',
                description='and the silver spoon...',
                image_url='https://i.gr-assets.com/foo.jpg',
            ),
            Book(
                goodreads_id="3836",
                isbn="0142437239",
                title="Don Quixote",
                author="Miguel de Cervantes",
                description="Windmills, Sancho Panza, etc.",
                image_url="not relevant, so not a real URL",
            ),
        ]

        with mock.patch.dict('os.environ', {'GOODREADS_DEV_KEY': 'fake-key'}):
            # pylint: disable=invalid-name
            with mock.patch.object(goodreads, 'ShelfReader') as ShelfReader:
                ShelfReader.return_value = fake_reader

                response = handler(
                    {'body': json.dumps(okay_payload)}, context=dummy_context
                )

        ShelfReader.assert_called_once_with('12345', 'fake-key')
        fake_reader.wanted_books.assert_called_once_with('custom-to-read')

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
                    '{"books": ['
                    '{"goodreads_id": "135479", "isbn": "0140285601", "title": "Cat\'s Cradle", "author": "Kurt Vonnegut Jr."}, '
                    '{"goodreads_id": "3836", "isbn": "0142437239", "title": "Don Quixote", "author": "Miguel de Cervantes"}'
                    ']}'
                ),
            },
        )
