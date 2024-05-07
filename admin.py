import streamlit as st
import pymongo
import os
import lib.common as common
common.init_session_state()

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
# Check if the file exist
with st.sidebar:
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
            # Get the database name
            db_name = st.secrets["mongo_db"]["db"]
            # Drop the database
            client.drop_database(db_name)
            # Display a success message
            st.success("DATABASE DELETED")

    """
    * _Proudly Engineered in Boston by [Strolid's](http://strolid.ai) World Wide Team_
    * _Interested in vCons? [Learn More](https://docs.vcon.dev)_
    * _Looking for the IETF draft? [Read More](https://datatracker.ietf.org/doc/draft-petrie-vcon/)_
    * _Looking for partners? [Contact Us](mailto:sales@strolid.com)_
    * _Need help? [Support](mailto:support@strolid.com)_
    """


