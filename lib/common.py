# Setup the session state for the app
import streamlit as st
import os
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

def sidebar():
    with st.sidebar:
                    
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

