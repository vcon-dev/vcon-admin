import streamlit as st
import redis
import pandas as pd
import pymongo
import json
import os

"""

## Admin Portal

This is the admin portal for the system. It allows you to view the current configuration, and to make changes to it.

"""
# Initialize connection.
# Uses st.cache_resource to only run once.
@st.cache_resource
def init_connection():
    url = st.secrets["mongo_db"]["url"]
    return pymongo.MongoClient(url)

client = init_connection()

# Current directory in the container is /app
# Check if the file exists
if os.path.isfile("custom_info.md"):
    # Open the file and read its contents
    with open("custom_info.md", "r") as file:
        contents = file.read()

# Display the contents in the Streamlit app
st.markdown(contents)
