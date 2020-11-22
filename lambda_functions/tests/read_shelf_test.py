""" Tests the lambda function which reads from Goodreads shelves. """
# Bibliophile's import monkey-patches SSL via a `grequests` import
# It's important that this happen *before* boto3 imports SSL
# We can remove this once migrating away from grequests
import bibliophile  # isort: skip, pylint: disable=unused-import

import json
import unittest
from typing import List
from unittest import mock

import boto3
import yaml
from aws_lambda_context import LambdaContext
from moto import mock_dynamodb2

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


@mock_dynamodb2
class CachingTest(unittest.TestCase):
    """ Test the lambda function's caching behavior. """

    expected_books: List[Book] = [
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

    success_response = {
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
    }

    def setUp(self):
        dynamodb = boto3.resource('dynamodb')
        self.table = self.create_table(dynamodb)

        self.fake_reader = mock.Mock(spec=goodreads.ShelfReader)
        self.fake_reader.wanted_books.return_value = self.expected_books

    @staticmethod
    def create_table(dynamodb):
        """Create the DynamoDB table for shelvedBooks.

        This allows our unit tests to (jankily) recreate what serverless
        will actually apply in production.

        We could somehow try to connect `serverless` DynamoDB tooling
        with our Python tests, but this is simple enough.
        """
        # Read the table specification from serverless.yml
        # (The config there is just normal CloudFormation syntox)
        with open('serverless.yml') as serverless_config:
            config = yaml.safe_load(serverless_config)
        schema = config['resources']['Resources']['shelvedBooksTable']['Properties']

        # The `create_table` can't accept this specification via a resource
        # We'll just fall back to the low-level API to set this.
        ttl_conf = schema.pop('TimeToLiveSpecification')
        table = dynamodb.create_table(**schema)

        # Wait until the table exists.
        table.meta.client.get_waiter('table_exists').wait(TableName=schema['TableName'])
        assert table.table_status == 'ACTIVE'

        # For good measure, add the TTL configuration too
        client = boto3.client("dynamodb")
        client.update_time_to_live(
            TableName=schema['TableName'], TimeToLiveSpecification=ttl_conf
        )

        return table

    def tearDown(self):
        self.table.delete()

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

    def test_cache_miss(self):
        """ On a cache miss, we hit the API endpoint. """
        okay_payload = {'userId': '12345', 'shelf': 'custom-to-read'}

        with mock.patch.dict('os.environ', {'GOODREADS_DEV_KEY': 'fake-key'}):
            # pylint: disable=invalid-name
            with mock.patch.object(goodreads, 'ShelfReader') as ShelfReader:
                ShelfReader.return_value = self.fake_reader

                response = handler(
                    {'body': json.dumps(okay_payload)}, context=dummy_context
                )

        ShelfReader.assert_called_once_with('12345', 'fake-key')
        self.fake_reader.wanted_books.assert_called_once_with('custom-to-read')

        self.assertEqual(response, self.success_response)

    def test_cache_miss_then_hit(self):
        """ When there's a cache miss, we query the shelf & store results. """
        okay_payload = {'userId': '12345', 'shelf': 'custom-to-read'}

        with mock.patch.dict('os.environ', {'GOODREADS_DEV_KEY': 'fake-key'}):
            # pylint: disable=invalid-name
            with mock.patch.object(goodreads, 'ShelfReader') as ShelfReader:
                ShelfReader.return_value = self.fake_reader

                response = handler(
                    {'body': json.dumps(okay_payload)}, context=dummy_context
                )

        # The first call was a cache miss - we hit the API endpoint
        ShelfReader.assert_called_once_with('12345', 'fake-key')
        self.fake_reader.wanted_books.assert_called_once_with('custom-to-read')
        self.assertEqual(response, self.success_response)

        self.fake_reader.reset_mock()

        # However, the second call now has a cache hit!
        # pylint: disable=invalid-name
        with mock.patch.object(goodreads, 'ShelfReader') as ShelfReader:
            response2 = handler(
                {'body': json.dumps(okay_payload)}, context=dummy_context
            )
        self.assertEqual(response2, self.success_response)

        # We don't need to initialize a reader, nor request books
        ShelfReader.assert_not_called()
        self.fake_reader.wanted_books.assert_not_called()

    def test_cache_bypass(self):
        """ Users can request to ignore the cache entirely. """
        bypass_payload = {
            'userId': '12345',
            'shelf': 'custom-to-read',
            'skipCache': True,
        }

        # The first time we call, there's no cache to bypass.
        with mock.patch.dict('os.environ', {'GOODREADS_DEV_KEY': 'fake-key'}):
            # pylint: disable=invalid-name
            with mock.patch.object(goodreads, 'ShelfReader') as ShelfReader:
                ShelfReader.return_value = self.fake_reader

                response = handler(
                    {'body': json.dumps(bypass_payload)}, context=dummy_context
                )

        # We hit the API endpoint to get results
        ShelfReader.assert_called_once_with('12345', 'fake-key')
        self.fake_reader.wanted_books.assert_called_once_with('custom-to-read')
        self.assertEqual(response, self.success_response)

        # We recorded a result directly to the cache
        cached = self.table.get_item(Key={'userAndShelf': '12345-custom-to-read'})
        self.assertIn('Item', cached)
        self.assertCountEqual(
            [bk['title'] for bk in cached['Item']['books']],
            {"Cat's Cradle", "Don Quixote"},
        )

        # The second call would have a cache hit, but the caller is bypassing.
        # pylint: disable=invalid-name
        self.fake_reader.reset_mock()
        with mock.patch.dict('os.environ', {'GOODREADS_DEV_KEY': 'fake-key'}):
            with mock.patch.object(goodreads, 'ShelfReader') as ShelfReader:
                ShelfReader.return_value = self.fake_reader
                response2 = handler(
                    {'body': json.dumps(bypass_payload)}, context=dummy_context
                )
        self.assertEqual(response2, self.success_response)

        # We made a fresh call to get results
        self.fake_reader.wanted_books.assert_called_once_with('custom-to-read')
