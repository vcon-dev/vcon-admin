# Setup the session state for the app
import streamlit as st
import os
import pymongo
import yaml
from yaml.loader import SafeLoader
from elasticsearch import Elasticsearch
import requests

authenticator = None

def init_session_state():    
    # Set the document metadata
    st.set_page_config(
        page_title="vCon Admin",
        page_icon="🦦",
        layout="wide"
    )
    
    if "vcon_uuids" not in st.session_state:
        st.session_state.vcon_uuids = []
        
    # Setup the selected vCon
    if "selected_vcon" not in st.session_state:
        st.session_state.selected_vcon = None
        # Check to see if we have a query parameter
        if hasattr(st, 'query_params'):
            if 'uuid' in st.query_params:
                st.session_state.selected_vcon = st.query_params['uuid']
                     
    
def get_mongo_client():
    # Get the MongoDB connection
    url = st.secrets["mongo_db"]["url"]
    return pymongo.MongoClient(url)


def get_vcons(since = None, limit = None):
    # Get the vCons from the MongoDB collection, taking into account the since and limit parameters
    client = get_mongo_client()
    db = client.vcons
    collection = db.vcons
    query = {}
    if since:
        query['created_at'] = {'$gte': since}
    cursor = collection.find(query)
    if limit:
        cursor = cursor.limit(limit)
    return list(cursor)


def get_vcon(uuid):
    # Get a single vCon from the MongoDB collection
    client = get_mongo_client()
    db = client.vcons
    collection = db.vcons
    return collection.find_one({'uuid': uuid})

# Function to initialize the Elasticsearch connection
def get_es_client():
    url = st.secrets["elasticsearch"]["url"]
    username = st.secrets["elasticsearch"]["username"]
    password = st.secrets["elasticsearch"]["password"]
    ca_certs = st.secrets["elasticsearch"].get("ca_certs", None)
    
    if ca_certs and os.path.exists(ca_certs):
        return Elasticsearch(url, basic_auth=(username, password), ca_certs=ca_certs)
    else:
        return Elasticsearch(url, basic_auth=(username, password), verify_certs=False)

def get_conserver_config():
    # Get the config from the conserver API server
    url = st.secrets["conserver"]["api_url"] + "/config"
    auth_token = st.secrets["conserver"]["auth_token"]
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }
    
    # Get the config from the conserver API server
    response = requests.get(url, headers)
    # Check if the response was successful
    if response.status_code == 200:
        return response.json()
    
def sidebar():
    with st.sidebar:     
        # If there's an conserver API URL, display it
        if "conserver" in st.secrets:
            st.markdown(f"[Conserver API]({st.secrets['conserver']['api_url']}/docs)")
                                
        banner = '''
        * _Proudly Engineered in Boston by [Strolid's](http://strolid.ai) World Wide Team_
        * _Interested in vCons? [Learn More](https://docs.vcon.dev)_
        * _Looking for the IETF draft? [Read More](https://datatracker.ietf.org/doc/draft-petrie-vcon/)_
        * _Looking for partners? [Contact Us](mailto:sales@strolid.com)_
        * _Need help? [Support](mailto:support@strolid.com)_
        '''

        if os.path.isfile("custom_info.md"):
            with st.expander("Help"):
                # Open the file and read its contents
                with open("custom_info.md", "r") as file:
                    contents = file.read()

                    # Display the contents in the Streamlit app
                    st.markdown(contents)
            with st.expander("Danger Zone"):
                # Enable the user to delete the database
                if st.button("DELETE vCon DATABASE", key="delete_db", help="This will delete the entire database."):
                    client = get_mongo_client()

                    # Get the database name
                    db_name = st.secrets["mongo_db"]["db"]
                    # Drop the database
                    client.drop_database(db_name)
                    # Display a success message
                    st.success("DATABASE DELETED")

        st.markdown(banner)


