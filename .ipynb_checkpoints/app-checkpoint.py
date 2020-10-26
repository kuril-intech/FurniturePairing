from flask import Flask, render_template, session, request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
import pandas as pd
import datetime
import hashlib
import urllib
import numpy as np
import cv2

import base64
from detection import upload_to_gcs
from detection import generate_download_signed_url_v4
from detection import get_similar_products_uri
from detection import query_product
from detection import get_thumbnail
from detection import bucket2product
from retrieval import retrieval

app = Flask(__name__)
app.secret_key = 'keye'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://mkhoa:Mkhoa94@coderschool@10.127.96.3:3306/project'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
project_id = 'abstract-veld-289612'
location = 'asia-east1'
product_set_id = 'PAIR-Filter'
bucket_name = 'ftmle'
product_category= 'homegoods-v2'
color = [(255,0,0), 
         (0,255,0), 
         (0,0, 255), 
         (135, 170, 170), 
         (135, 100, 125), 
         (135, 100, 190), 
         (0, 255, 255), 
         (255, 255, 255),
        (255, 0, 255),
        (255, 255, 255)]

config = {
    "DEBUG": True, 
    "CACHE_TYPE": "simple",
    "CACHE_DEFAULT_TIMEOUT": 10000
}
app.config.from_mapping(config)
cache = Cache(app)

class ProductHeader(db.Model): # Urunler
    __tablename__ = "ProductHeader"
    id = db.Column(db.Integer, primary_key=True, autoincrement = True, unique=True)
    website = db.Column(db.String(100),nullable=True)
    category = db.Column(db.String(255),nullable=True)
    category_url = db.Column(db.Text,nullable=True)
    image = db.Column(db.Text,nullable=True)
    product = db.Column(db.Text,nullable=False)
    price = db.Column(db.String(255),nullable=True)
    url = db.Column(db.Text,nullable=True)

def search_product(bucket_name, blob_name):
    serving_url = generate_download_signed_url_v4(bucket_name, blob_name)
    res = get_similar_products_uri(project_id, location, product_set_id, product_category,
        image_uri=serving_url, filter='')
    return res, serving_url

def url_to_image(url):
    # download the image, convert it to a NumPy array, and then read
    # it into OpenCV format
    resp = urllib.request.urlopen(url)
    image = np.asarray(bytearray(resp.read()), dtype="uint8")
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    # return the image
    return image

def draw_bounding(res, img_url):
    img = url_to_image(img_url)
    font = cv2.FONT_HERSHEY_SIMPLEX
    fontScale = 2
    fontColor = (0,255,255)
    lineType = 5
    string = ''
    for i in range(len(res)):
        w = img.shape[1]
        h = img.shape[0]
        x1 = int(res[i].bounding_poly.normalized_vertices[0].x * w)
        y1 = int(res[i].bounding_poly.normalized_vertices[0].y * h)
        x2 = int(res[i].bounding_poly.normalized_vertices[2].x * w)
        y2 = int(res[i].bounding_poly.normalized_vertices[2].y * h)
        result = cv2.rectangle(img,(x1,y1), (x2,y2), color[i], thickness=5)
        result = cv2.putText(result,str(i), (x1, y1), font, fontScale, fontColor, lineType)  
    result = cv2.imencode('.jpg', result)[1].tostring()
    fname = str(datetime.datetime.now().date()) + '_' + str(datetime.datetime.now().time()).replace(':', '.') + '.jpg'
    blob_name = 'Images/Bounding/' + fname
    upload_to_gcs(result, bucket_name, blob_name)  
    return blob_name

@app.route('/')
def index():
    return render_template('index.html') 

@app.route('/store')
@cache.cached(timeout=1000)
def store():
    header=ProductHeader.query.filter((ProductHeader.website == 'aconcept-vn.com')).limit(60)
    return render_template('store.html', Header=header) 

@app.route('/shopthelook')
def shopthelook():
  return render_template('shopthelook.html')

@app.route('/shopthelook', methods = ['POST'])
def upload_file():
    uploaded_file = request.files['file']
    content = uploaded_file.read()
    if uploaded_file.filename != '':
        fname = str(datetime.datetime.now().date()) + '_' + str(datetime.datetime.now().time()).replace(':', '.') + '-' + uploaded_file.filename
        blob_name = 'Images/Uploads/' + fname
        response = upload_to_gcs(content, bucket_name, blob_name)
    
    res, serving_url = search_product(bucket_name, blob_name)
    
    result = []
    for i in range(len(res)):    
        for j in range(len(res[i].results)):
            d = {}
            d['object'] = i
            d['idx'] = int(res[i].results[j].product.name.split('/', -1)[-1])
            d['score'] = res[i].results[j].score
            result.append(d)
    
    result = pd.DataFrame(result)  
    query = pd.DataFrame(result['idx'].apply(query_product).tolist(), columns=['idx', 'Website', 'Name', 'Image', 'URL', 'Category'])
    df = result.merge(query)
    df = df.drop_duplicates('idx')
    df = df[df['score'] > 0.5].sort_values(by='Category')
    
    bounding_img = draw_bounding(res, serving_url)
    bounding_img = generate_download_signed_url_v4(bucket_name, bounding_img)
    
    return render_template('shopthelook.html', product_search=response, tables=[df.to_html(classes='data')], titles=df.columns.values,
                          results = df, bounding_box=bounding_img)

@app.route('/pair')
def pair():
    product_id = request.args.get('product_id', type = int)
    if product_id:
        blob_name = get_thumbnail(product_id)[1]
        retrieval_result = retrieval(blob_name)
        results = []
        for i in retrieval_result:
            d = {}
            path2product = bucket2product(i)
            d['id'] = path2product[0]
            d['name'] = path2product[1]
            d['url'] = path2product[2]
            d['image'] = generate_download_signed_url_v4(bucket_name, i)
            results.append(d)
        
        results = pd.DataFrame(results, columns=['id', 'name', 'url', 'image'])

        return render_template('pair.html', retrieval=retrieval_result, pair_result=results)
    else:
        return render_template('pair.html')

@app.route('/pair', methods = ['POST'])
def pair_upload_file():
    uploaded_file = request.files['file']
    content = uploaded_file.read()
    if uploaded_file.filename != '':
        fname = str(datetime.datetime.now().date()) + '_' + str(datetime.datetime.now().time()).replace(':', '.') + '-' + uploaded_file.filename
        blob_name = 'Images/Uploads/' + fname
        response = upload_to_gcs(content, bucket_name, blob_name)

    if blob_name:
        retrieval_result = retrieval(blob_name)
        results = []
        for i in retrieval_result:
            d = {}
            path2product = bucket2product(i)
            d['id'] = path2product[0]
            d['name'] = path2product[1]
            d['url'] = path2product[2]
            d['image'] = generate_download_signed_url_v4(bucket_name, i)
            results.append(d)
        
        results = pd.DataFrame(results, columns=['id', 'name', 'url', 'image'])
    
    return render_template('pair.html', retrieval=retrieval_result, pair_result=results)

@app.route('/login', methods=['GET'])
def login():        
    return render_template('login.html')

if __name__ == '__main__':
  app.run(debug=True, host='0.0.0.0', port=8085)

 