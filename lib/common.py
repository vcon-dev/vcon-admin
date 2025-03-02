# Setup the session state for the app
import streamlit as st
import os
import pymongo
import yaml
from yaml.loader import SafeLoader
from elasticsearch import Elasticsearch
import requests
import logging
from pymongo import MongoClient
from functools import wraps

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vcon-admin")

authenticator = None

# MongoDB Connection Management
_mongo_client = None

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
                     
    
def convert_to_isoformat(vcon_doc):
    """Convert the created_at and dialog.start to isoformat."""
    if 'created_at' in vcon_doc:
        vcon_doc['created_at'] = vcon_doc['created_at'].isoformat()
    if 'dialog' in vcon_doc:
        for dialog in vcon_doc['dialog']:
            if 'start' in dialog:
                dialog['start'] = dialog['start'].isoformat()
    return vcon_doc

def get_mongo_client():
    """Get or create a MongoDB client with connection pooling."""
    global _mongo_client
    if _mongo_client is None:
        try:
            url = st.secrets["mongo_db"]["url"]
            # Use connection pooling with appropriate settings
            _mongo_client = MongoClient(
                url, 
                maxPoolSize=10,
                retryWrites=True,
                serverSelectionTimeoutMS=5000
            )
            # Verify connection is working
            _mongo_client.admin.command('ping')
            logger.info("MongoDB connection established")
        except Exception as e:
            logger.error(f"MongoDB connection error: {str(e)}")
            st.error(f"Database connection error: {str(e)}")
            raise e
    return _mongo_client

def get_vcon_db():
    """Get the vCon database."""
    client = get_mongo_client()
    db_name = st.secrets["mongo_db"]["db"]
    return client[db_name]

def get_vcon_collection():
    """Get the vCon collection."""
    db = get_vcon_db()
    collection_name = st.secrets["mongo_db"]["collection"]
    return db[collection_name]

def mongo_error_handler(func):
    """Decorator to handle MongoDB errors consistently."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except pymongo.errors.ConnectionFailure as e:
            logger.error(f"MongoDB connection failure: {str(e)}")
            st.error("Database connection failed. Please try again later.")
        except pymongo.errors.OperationFailure as e:
            logger.error(f"MongoDB operation failure: {str(e)}")
            st.error(f"Database operation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            st.error(f"An unexpected error occurred: {str(e)}")
    return wrapper

# Enhanced vCon retrieval functions
@mongo_error_handler
def get_vcons(since=None, limit=None, sort_by="created_at", sort_order="descending"):
    """Get vCons with better pagination and sorting support."""
    collection = get_vcon_collection()
    query = {}
    if since:
        query['created_at'] = {'$gte': since}
    
    # Handle sorting
    sort_direction = pymongo.DESCENDING if sort_order.lower() == "descending" else pymongo.ASCENDING
    
    cursor = collection.find(query).sort(sort_by, sort_direction)
    if limit:
        cursor = cursor.limit(limit)
    
    vcons = list(cursor)
    for vcon in vcons:
        convert_to_isoformat(vcon)
    return vcons


@mongo_error_handler
def get_vcon(uuid):
    """Get a single vCon by UUID with error handling."""
    collection = get_vcon_collection()
    vcon  = collection.find_one({'uuid': uuid})
    convert_to_isoformat(vcon)
    return vcon

@mongo_error_handler
def count_vcons(query=None):
    """Count vCons with optional filter query."""
    collection = get_vcon_collection()
    return collection.count_documents(query or {})

@mongo_error_handler
def update_vcon(uuid, update_data):
    """Update a vCon document."""
    collection = get_vcon_collection()
    result = collection.update_one({'uuid': uuid}, {'$set': update_data})
    return result.modified_count

@mongo_error_handler
def insert_vcon(vcon_data):
    """Insert a new vCon document."""
    collection = get_vcon_collection()
    result = collection.replace_one({'_id': vcon_data['uuid']}, vcon_data, upsert=True)
    return result

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
        "x-conserver-api-token": f"{auth_token}",
        "accept": "application/json"
    }
    
    # Get the config from the conserver API server
    response = requests.get(url, headers=headers)
    
    # Check if the response was successful
    if response.status_code == 200:
        return response.json()
    else:
        return None
    
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


        def deepgram_transcript_to_markdown(transcript_data):
            """
            Convert a Deepgram transcript into markdown format for display.
            
            Args:
                transcript_data (dict): The raw transcript data from Deepgram.
                
            Returns:
                str: The formatted markdown string.
            """
            if not transcript_data or 'paragraphs' not in transcript_data:
                return ""
            
            paragraphs = transcript_data['paragraphs']['paragraphs']
            markdown_lines = []
            
            for paragraph in paragraphs:
                for sentence in paragraph['sentences']:
                    markdown_lines.append(sentence['text'])
                markdown_lines.append("")  # Add a blank line between paragraphs
            
            return "\n".join(markdown_lines)
