# Setup the session state for the app
import streamlit as st
import pymongo

def init_session_state():
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
