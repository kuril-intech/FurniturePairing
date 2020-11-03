import airflow
import urllib
import pymysql
import os
import pandas as pd

from google.cloud import storage
from urllib.parse import urlparse
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from datetime import date, timedelta, datetime

project_id = 'optical-scarab-285012'
bucket_name = 'mle-project'
path = 'Images/Thumbnails/'
storage_client = storage.Client.from_service_account_json("/home/FurniturePairing/credentials/abstract-veld-289612-327ddac80eba.json")

#Setup Connection to mysql database
conn = pymysql.connect(
    host='localhost',
    port=int(3306),
    user="mkhoa",
    passwd='CoderSchool@2020',
    db="Pair",
    charset='utf8mb4')

cur = conn.cursor()

def upload_blob(bucket_name, url, path, prefix):
    '''
    Upload to Google Cloud Storage

    '''   
    file = urllib.request.urlopen(url)
    content_type = file.info().get_content_type()
    file_name = os.path.basename(urlparse(url).path)
    dest = path + str(prefix) + '-' + file_name
    
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(dest)

    blob.upload_from_string(file.read(), content_type=content_type)
    
    return dest

def query_url():
    '''
    
    '''
    query = '''
    SELECT id, image
    FROM project.ProductHeader
    WHERE image like 'http%';;
    '''
    try:
        cur.execute(query)
    except Exception as err:
        print('ERROR BY INSERT:', err)
    result = cur.fetchall()
    df = pd.DataFrame(result, columns=['id', 'url'])
    return df

def insert_filepath(id, url, bucket, bucket_path):
    '''
    
    '''
    query = f'''
    INSERT INTO Files(id, url, bucket, bucket_path)
    VALUES('{id}', '{url}', '{bucket}', '{bucket_path}');
    '''
    try:
        cur.execute(query)
        conn.commit()
    except Exception as err:
        print('ERROR BY INSERT:', err)

def saving_image(**kwargs):
    '''

    '''
    ti = kwargs['ti']
    df = ti.xcom_pull(task_ids='query_url')
    df = df[:5]
    for i in df.values:
        id = i[0]
        url = i[1]
        filepath = upload_blob(bucket_name, url, path, id)
        print('Uploaded' + str(id))
        insert_filepath(id, url, bucket_name, filepath)
        print('Recorded' + str(id))

# --------------------------------------------------------------------------------
# set default arguments
# --------------------------------------------------------------------------------
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2020, 10, 1, 10, 00, 00),
    'concurrency': 1,
    'retries': 0
}

# --------------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------------

dag = DAG('save_img2bucket',
         catchup=False,
         default_args=default_args,
         schedule_interval=None)

opr_query_url = PythonOperator(task_id='query',
                                    python_callable=query_url, 
                                    provide_context=True,
                                    dag=dag)

opr_saving_image = PythonOperator(task_id='saving',
                                    python_callable=saving_image, 
                                    dag=dag,
                                    provide_context=True)

opr_query_url >> opr_saving_image


