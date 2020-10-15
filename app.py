import streamlit as st
import pandas as pd
import os
import sys
import datetime
import filetype
import urllib
import numpy as np
import cv2

from pathlib import Path
from enum import Enum
from io import BytesIO, StringIO
from typing import Union
from detection import upload_to_gcs
from detection import generate_download_signed_url_v4
from detection import get_similar_products_uri
from detection import query_product

#sys.setrecursionlimit(15000)
#script_location = Path(__file__).absolute().parent
#Parameter
product_set_id = 'PAIR'
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

STYLE = """
<style>
img {
    max-width: 100%;
}
</style>
"""

def main():
    '''Main function that will run the whole app
    
    '''
    # Once we have the dependencies, add a selector for the app mode on the sidebar.
    st.title('Pair: A Cross-Category Furniture Recommendation Engine')
    st.sidebar.title("What to do")
    st.set_option('deprecation.showfileUploaderEncoding', False)
    app_mode = st.sidebar.selectbox("Choose the app mode",
        ["Introduction", "Furniture Detection", "Furniture Pairing"])
    if app_mode == "Introduction":
        st.sidebar.success('To continue select "Run the app".')
        intro()
    elif app_mode == "Furniture Detection":
        st.write('Furniture Detection')
    elif app_mode == "Furniture Pairing":
        st.write('Furniture Detection')

def url_to_image(url):
    # download the image, convert it to a NumPy array, and then read
    # it into OpenCV format
    resp = urllib.request.urlopen(url)
    image = np.asarray(bytearray(resp.read()), dtype="uint8")
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    # return the image
    return image

def get_product(n, res):
    for i in range(3):
        idx = res[n].results[i].product.name.split('/', -1)[-1]
        info = query_product(idx)
        st.image(info[0][3])
        st.markdown(f'''Product ID: {info[0][0]}''')
        st.markdown(f'''[Name: {info[0][2]}]({info[0][4]})''')
        
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
        result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        
        for label in res[i].object_annotations:
            name = label.name
            score = str(label.score)
            
        x = 'Object ' + str(i) + ': ' + name + ' - ' + score + '\n'
        string += x
    
    st.image(result)
    st.text(string)

def search_product(bucket_name, blob_name):
    serving_url = generate_download_signed_url_v4(bucket_name, blob_name)
    res = get_similar_products_uri(project_id, location, product_set_id, product_category,
        image_uri=serving_url, filter='')
    return res, serving_url
        
# Introduction
def intro():
    """
    Upload File on Streamlit Code
    
    """
    st.markdown('# Upload Image')
    fileTypes = ["png", "jpg", "jpeg"]  
    st.markdown(STYLE, unsafe_allow_html=True)
    file = st.file_uploader("Upload image of furnitures", type=fileTypes)
    show_file = st.empty()
    if not file:
        show_file.info("Please upload a file of type: " + ", ".join(["png", "jpg", "jpeg"]))
        return
    content = file.getvalue()
    if isinstance(file, BytesIO):
        show_file.image(file)
        try:
            kind = filetype.guess(file)
            fname = str(datetime.datetime.now().date()) + '_' + str(datetime.datetime.now().time()).replace(':', '.')
            bucket_name = 'ftmle'
            blob_name = 'Images/Uploads/' + fname + '.' + kind.extension
            res = upload_to_gcs(content, bucket_name, blob_name)
            st.write('Path: ' + 'gs://' + bucket_name + '/' + str(blob_name))
            st.write('Response Code: ' + str(res))
        except:
            st.write('Error')
    else:
        data = pd.read_csv(file)
        st.dataframe(data.head(10))
        file.close()   
    st.markdown('# Object Detection')
    res, serving_url = search_product(bucket_name, blob_name)
    n = len(res)
    st.write('Detected ' + str(n) + ' objects')
    draw_bounding(res, serving_url)
    
    st.markdown('# Similar Products')
    for i in range(n):
        st.markdown(f'''## Object {str(i)}''')
        get_product(i, res)
    
if __name__ == "__main__":
    main()