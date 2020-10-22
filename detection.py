import pymysql
import datetime
import requests

from google.cloud import vision
from google.cloud import storage


#Parameter
project_id = 'abstract-veld-289612'
location = 'asia-east1'
product_set_id = 'PAIR'
bucket_name = 'ftmle'
storage_client = storage.Client.from_service_account_json("./Credentials/abstract-veld-289612-327ddac80eba.json")

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

def get_similar_products_uri(
        project_id, location, product_set_id, product_category,
        image_uri, filter=''):
    """Search similar products to image.
    Args:
        project_id: Id of the project.
        location: A compute region name.
        product_set_id: Id of the product set.
        product_category: Category of the product.
        image_uri: Cloud Storage location of image to be searched.
        filter: Condition to be applied on the labels.
        Example for filter: (color = red OR color = blue) AND style = kids
        It will search on all products with the following labels:
        color:red AND style:kids
        color:blue AND style:kids
    """
    # product_search_client is needed only for its helper methods.
    product_search_client = vision.ProductSearchClient()
    image_annotator_client = vision.ImageAnnotatorClient()

    # Create annotate image request along with product search feature.
    image_source = vision.ImageSource(image_uri=image_uri)
    image = vision.Image(source=image_source)

    # product search specific parameters
    product_set_path = product_search_client.product_set_path(
        project=project_id, location=location,
        product_set=product_set_id)
    product_search_params = vision.ProductSearchParams(
        product_set=product_set_path,
        product_categories=[product_category])
    image_context = vision.ImageContext(
        product_search_params=product_search_params)

    # Search products similar to the image.
    response = image_annotator_client.product_search(
        image, image_context=image_context)
    
    res_search = response.product_search_results
    res_poly = response.product_search_results.product_grouped_results
    
    return res_poly

#Setup Connection to mysql database
conn = pymysql.connect(
    host='10.127.96.3',
    port=int(3306),
    user="mkhoa",
    passwd='Mkhoa94@coderschool',
    db="project",
    charset='utf8mb4')

cur = conn.cursor()

def query_product(id):
    '''
    
    '''
    query = f'''
    SELECT a.id, a.website, a.product, a.image, a.url, b.group_category
    FROM project.ProductHeader a
    LEFT JOIN project.category b ON a.category = b.Category
    WHERE a.id = '{id}'
    '''
    try:
        cur.execute(query)
    except Exception as err:
        print('ERROR BY SELECT:', err)
    result = cur.fetchone()
    return result

def get_thumbnail(id):
    '''
    
    '''
    query = f'''
    SELECT id, bucket_path
    FROM project.Files
    WHERE id = '{id}' AND bucket_path like '%Thumbnails%'
    '''
    try:
        cur.execute(query)
    except Exception as err:
        print('ERROR BY SELECT:', err)
    result = cur.fetchone()
    return result

def bucket2product(bucket_path):
    '''
    Reverse thumbnail bucket path to query product information
    
    
    '''
    query = f'''
    SELECT a.id, a.product, a.url
    FROM project.ProductHeader a
    LEFT JOIN project.Files b ON a.id = b.id
    WHERE b.bucket_path = '{bucket_path}'
    '''
    try:
        cur.execute(query)
    except Exception as err:
        print('ERROR BY SELECT:', err)
    result = cur.fetchone()
    return result




    

