import airflow
import pandas as pd
import requests
import selenium
import time
import pymysql
import json
import re

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from datetime import date, timedelta

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from httplib2 import Http
from json import dumps

driver = webdriver.Chrome(executable_path='/usr/bin/chromedriver', options = options)
def push_notification(message):
    """Hangouts Chat incoming webhook quickstart.
    
    """
    url = 'https://chat.googleapis.com/v1/spaces/AAAAaREeoeA/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=DQ41G8_LUeuw2Tj_4s78qlmjpA5loEL9gZRdq1N9hOo%3D'
    bot_message = {
        'text' : message}
    message_headers = {'Content-Type': 'application/json; charset=UTF-8'}

    http_obj = Http()

    response = http_obj.request(
        uri=url,
        method='POST',
        headers=message_headers,
        body=dumps(bot_message),)

def houzz_category(url):
    '''
    Crawling category page of Houzz


    '''
    houzz = requests.get(url)
    soup = BeautifulSoup(houzz.text, 'html.parser')
    soup = soup.body.find_all('a', {'class': 'department-card spf-link'})
    category = []
    for i in soup:
        try:
            d = {'Category': '', 'URL': ''}
            d['Category'] = i.text
            d['URL'] = i['href']
            category.append(d)
        except:
            print('Error')
    return category

def houzz_sub_category(url):
    '''
    Crawling Sub-Category link

    '''
    houzz = requests.get(url)
    soup = BeautifulSoup(houzz.text, 'html.parser')
    soup = soup.body.find_all('div', {'class': 'hz-browse-top-category__card-wrapper'})
    category = []
    for i in soup:
        try:
            d = {'Category': '', 'URL': ''}
            d['Category'] = i.text
            d['URL'] = i.a['href']
            category.append(d)
        except:
            print('Error')
    return category

def houzz_header(url):
    '''
    Get product header data and insert into database
    
    '''
    driver.get(url)
    time.sleep(10)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(10)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    next_url = soup.body.find('a', {'class': 'hz-pagination-link--next'})
    product_list = soup.body.find_all('a', {'class': 'hz-product-card__link'})
    
    if next_url != None:
        for i in product_list:
            try:          
                website = 'houzz.com'
                category = soup.body.h1.text
                category_url = url
                product = i.find('span', {'class': 'hz-product-card__product-title'}).text
                image = i.find('source')['srcset']
                price = i.find('span', {'class': 'hz-product-price--final'}).text
                product_url = i['href']
                push_notification('Scrapping at ' + product_url)
                insert_to_categories(website, category, category_url, product, image, price, product_url)
            except:
                push_notification('Error as ' + url)
        push_notification('Next Page at :' + 'https://houzz.com' + next_url['href'])
        houzz_header('https://houzz.com' + next_url['href'])
    else:
         for i in product_list:
            try:
                website = 'houzz.com'
                category = soup.body.h1.text
                category_url = url
                product = i.find('span', {'class': 'hz-product-card__product-title'}).text
                image = i.find('source')['srcset']
                price = i.find('span', {'class': 'hz-product-price--final'}).text
                product_url = i['href']
                push_notification('Scrapping at ' + product_url)
                insert_to_categories(website, category, category_url, product, image, price, product_url)
            except:
                push_notification('Error as ' + url)

#Setup Connection to mysql database
conn = pymysql.connect(
    host='localhost',
    port=int(3306),
    user="mkhoa",
    passwd='CoderSchool@2020',
    db="Pair",
    charset='utf8mb4')

cur = conn.cursor()  

#Insert into Category Table
def insert_to_categories(website, category, category_url, product, image, price, url):
    '''
    
    '''
    query = f'''
    INSERT INTO ProductHeader(website, category, category_url, product, image, price, url)
    VALUES('{website}', '{category}', '{category_url}', '{product}', '{image}', '{price}', '{url}');
    '''
    try:
        cur.execute(query)
        conn.commit()
    except Exception as err:
        print('ERROR BY INSERT:', err)


# --------------------------------------------------------------------------------
# set default arguments
# --------------------------------------------------------------------------------
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': airflow.utils.dates.days_ago(2),
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}