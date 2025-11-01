'''
This script provides functionality to access the cloud object storage for the
Maritim Situational Awe
'''

import logging
import os

import ibm_boto3
from ibm_botocore.client import ClientError
from ibm_botocore.exceptions import ClientError

from src.utilities.logger_config import logger
from src.utilities.profiling import timeit


@timeit
def retrieve_buckets():
    logger.debug("Retrieving list of buckets")
    try:
        buckets = list(cos_resource.buckets.all())
        if logger.level == logging.DEBUG:
            for bucket in buckets:
                logger.debug("Bucket Name: {0}".format(bucket.name))
        return buckets
    except ClientError as be:
        logger.error("CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        logger.error("Unable to retrieve list buckets: {0}".format(e))


@timeit
def retrieve_all_contents_v2(bucket, max_keys=100, filter='', delimiter=''):
    '''
    returns the bucket content as list of object (names, size) tuple or raises exception
    '''
    logger.info("Retrieving bucket content from: {0} in chunks of {1} #keys filtered by {2}.".format(
        bucket, max_keys, filter))
    all_files = []
    try:
        more_results = True
        next_marker = ''

        while (more_results):
            response = cos_client.list_objects(Bucket=bucket, 
                                               MaxKeys=max_keys,
                                               Marker = next_marker,
                                               Prefix=filter,
                                               Delimiter=delimiter)
            files = response["Contents"]
            all_files += files
            if logger.isEnabledFor(logging.DEBUG):
                for file in files:
                    logger.debug("Item: {0} ({1} bytes).".format(
                        file["Key"], file["Size"]))

            more_results = response["IsTruncated"]
            next_marker = response["NextMarker"]

    except ClientError as be:
        logger.error("CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        logger.error("Unable to retrieve bucket contents: {0}".format(e))

    return all_files


@timeit
def retrieve_all_contents(bucket):
    '''
    returns the bucket content as list of object (names, size) tuple or raises exception
    '''
    logger.info("Retrieving bucket content from: {0}".format(bucket))
    files = []
    try:
        files = cos_resource.Bucket(bucket).objects.all()
        if logger.isEnabledFor(logging.DEBUG):
            for file in files:
                logger.debug("Item: {0} ({1} bytes).".format(
                    file.key, file.size))

    except ClientError:
        logger.error("CLIENT ERROR:", exc_info=1)
        raise
    except Exception:
        logger.error("Unable to retrieve list of bucket content!", exc_info=1)
        raise

    return list(files)


def copy_from(bucket, file_key, destination):
    '''
    Copy the file with file_key from the bucket to the full qualified destination.

    Parameters:
    bucket - name of the bucket with the file
    file_key - identifier of the fil in the bucket
    destination - full qualified filename to copy to

    returns True on success, else logs an error and returns False
    '''
    success = True
    try:
        logger.debug('Retrieving item from bucket {0} with name {1}'
                     .format(bucket, file_key))

        cos_resource.Object(bucket, file_key).download_file(destination)

    except ClientError as be:
        logger.error("CLIENT ERROR: {0}".format(be), exc_info=1)
        success = False
    except Exception as e:
        logger.error("Unable to retrieve file contents: %s" % e, exc_info=1)
        success = False
    else:
        logger.debug('File copied from cos')

    return success


def download_file(bucket, file_key, base_dir, file_name):
    '''
    downloads object with file_key from bucket to given base_dir with file_name.

    returns True on success, else logs an error and returns False
    '''
    success = True
    try:
        logger.info(
            'Retrieving item from bucket {0} with name {1}'.format(bucket, file_key))

        cos_resource.Object(bucket, file_key).download_file(
            os.path.join(base_dir, file_name))
    except ClientError as be:
        logger.error("CLIENT ERROR: {0}".format(be), exc_info=1)
        success = False
    except Exception as e:
        logger.error("Unable to retrieve file contents: %s" % e, exc_info=1)
        success = False
    else:
        logger.info('File Downloaded')

    return success


def download_fileobj(bucket, file_key, fileobj):
    '''
    downloads object with file_key from bucket to given filelike object fileobj.

    returns True on success, else logs an error and returns False
    '''
    success = True
    try:
        logger.info(
            'Retrieving item from bucket {0} with name {1}'.format(bucket, file_key))

        cos_resource.Object(bucket, file_key).download_fileobj(fileobj)
    except ClientError as be:
        logger.error("CLIENT ERROR: {0}".format(be), exc_info=1)
        success = False
    except Exception as e:
        logger.error("Unable to retrieve file contents: %s" % e, exc_info=1)
        success = False
    else:
        logger.info('File retrieved')

    return success


cos_resource = ibm_boto3.resource("s3",
                                  endpoint_url='https://s3.ibmlab.de',
                                  aws_access_key_id='ibm-consulting-user-yk2u',
                                  aws_secret_access_key='Pass-cm6ts4g2'
                                  )
cos_client = ibm_boto3.client("s3",
                              endpoint_url='https://s3.ibmlab.de',
                              aws_access_key_id='ibm-consulting-user-yk2u',
                              aws_secret_access_key='Pass-cm6ts4g2'
                              )
