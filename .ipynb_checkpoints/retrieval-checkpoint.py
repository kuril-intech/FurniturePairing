# -*- coding: utf-8 -*-
import tensorflow as tf
import pickle

from google.cloud import storage
from annoy import AnnoyIndex

project_id = 'abstract-veld-289612'
bucket_name = 'ftmle'
storage_client = storage.Client.from_service_account_json("./credentials/abstract-veld-289612-327ddac80eba.json")

def load_bucket_image(path):
    '''
    Load GCS iamge from bucket
    
    '''
    path = str(path.numpy().decode("utf-8"))
    blob = storage_client.bucket(bucket_name).get_blob(path)
    img = blob.download_as_string()

    return img

def preprocess_image(bucket_path):
    '''
    Preprocess image from bucket path
    
    '''
    img = tf.py_function(load_bucket_image, [bucket_path], tf.string)
    img = tf.image.decode_image(img, channels=3, expand_animations = False)
    img = tf.image.resize(img, (128, 128))
    img = img/255
    img = tf.cast(img, tf.float32)

    return img

# The tuples are unpacked into the positional arguments of the mapped function
def load_and_preprocess_candidate(path):
  return preprocess_image(path)

def load_index_model():
    tower1_model = tf.keras.models.load_model('./model/Retrieval_tower1.h5', compile=False)
    with open('./model/candidate_to_path.p', 'rb') as handle:
        candidate_to_path = pickle.load(handle)
    
    return tower1_model, candidate_to_path

def retrieval(candidate):
    tower1_model, candidate_to_path = load_index_model()
    index = AnnoyIndex(32, "dot")
    index.load('./model/index.ann')
    x = load_and_preprocess_candidate(candidate)
    x = tf.expand_dims(x, axis=0)
    query_embedding = tower1_model(x)
    candidates = index.get_nns_by_vector(query_embedding[0], 8)
    result = [candidate_to_path[x].decode('utf-8') for x in candidates]
    
    return result


