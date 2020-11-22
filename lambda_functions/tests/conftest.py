"""
This special file is read by `pytest` at initialization!
"""
import os

# Initializing the dynamodb resource with boto3 will fail without a default region
# We'll always mock it away with moto, but set a valid region anyway.
os.environ['AWS_DEFAULT_REGION'] = 'us-west-1'
