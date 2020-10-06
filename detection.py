import urllib
import pymysql
import os
import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt
import cv2
import math
import google.auth
import datetime
import six
import requests


from google.cloud import vision
from google.cloud import storage
from skimage import io
from six.moves.urllib.parse import quote
from PIL import Image

#Parameter
project_id = 'abstract-veld-289612'
bucket_name = 'ftmle'
storage_client = storage.Client.from_service_account_json("./Credentials/abstract-veld-289612-327ddac80eba.json")
blob = 'Images/Products/146331-0-home-design.jpg'

def generate_download_signed_url_v4(bucket_name, blob_name):
    """Generates a v4 signed URL for downloading a blob.

    Note that this method requires a service account key file. You can not use
    this if you are using Application Default Credentials from Google Compute
    Engine or from the Google Cloud SDK.
    """
    # bucket_name = 'your-bucket-name'
    # blob_name = 'your-object-name'

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    url = blob.generate_signed_url(
        version="v4",
        # This URL is valid for 15 minutes
        expiration=datetime.timedelta(minutes=15),
        # Allow GET requests using this URL.
        method="GET",
    )

    # print("Generated GET signed URL:")
    # print(url)
    # print("You can use this URL with any user agent, for example:")
    # print("curl '{}'".format(url))
    return url
#print(generate_download_signed_url_v4(bucket_name, blob))


def generate_upload_signed_url_v4(bucket_name, blob_name):
    """Generates a v4 signed URL for uploading a blob using HTTP PUT.

    Note that this method requires a service account key file. You can not use
    this if you are using Application Default Credentials from Google Compute
    Engine or from the Google Cloud SDK.
    """
    # bucket_name = 'your-bucket-name'
    # blob_name = 'your-object-name'

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    url = blob.generate_signed_url(
        version="v4",
        # This URL is valid for 15 minutes
        expiration=datetime.timedelta(minutes=15),
        # Allow PUT requests using this URL.
        method="PUT",
        content_type="application/octet-stream",
    )

    print("Generated PUT signed URL:")
    print(url)
    print("You can use this URL with any user agent, for example:")
    print(
        "curl -X PUT -H 'Content-Type: application/octet-stream' "
        "--upload-file my-file '{}'".format(url)
    )
    return url

# test_img = Image.open('test.jpg')
# print(te)
# img = open('test.jpg', 'rb')
# blob_name = 'Images/Uploads/test.jpg'
def upload_to_gcs(img, bucket_name, blob_name):
    upload_url = generate_upload_signed_url_v4(bucket_name, blob_name)
    headers = {'content-type': 'application/octet-stream'}
    response = requests.put(upload_url, data=img, headers=headers)
    return response.status_code


    

