import streamlit as st
import pandas as pd
import os
import sys
import datetime

from pathlib import Path
from enum import Enum
from io import BytesIO, StringIO
from typing import Union
from detection import upload_to_gcs


sys.setrecursionlimit(15000)
script_location = Path(__file__).absolute().parent

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
        
# Introduction
def intro():
    """
    Upload File on Streamlit Code
    
    """
    fileTypes = ["csv", "png", "jpg"]  
    st.markdown(STYLE, unsafe_allow_html=True)
    file = st.file_uploader("Upload file", type=fileTypes)
    show_file = st.empty()
    if not file:
        show_file.info("Please upload a file of type: " + ", ".join(["csv", "png", "jpg"]))
        return
    content = file.getvalue()
    if isinstance(file, BytesIO):
        show_file.image(file)
        try:
            fname = str(datetime.datetime.now().date()) + '_' + str(datetime.datetime.now().time()).replace(':', '.')
            bucket_name = 'ftmle'
            blob_name = 'Images/Uploads/test.jpg'
            res = upload_to_gcs(content, bucket_name, blob_name)
            st.write('Response Code: ' + res)
            st.write('Show File: ' + fname)
        except:
            st.write('Error')
    else:
        data = pd.read_csv(file)
        st.dataframe(data.head(10))
        file.close()

def file_selector(folder_path='.'):
    filenames = os.listdir(folder_path)
    selected_filename = st.selectbox('Select a file', filenames)
    return os.path.join(folder_path, selected_filename)

if __name__ == "__main__":
    main()