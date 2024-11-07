# This file takes the local vCons and indexes them in Elasticsearch. It also provides a search interface for the vCons.
#
import streamlit as st
import pymongo
import json
import lib.common as common
import requests
import os
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from datetime import datetime
from lib.common import get_es_client

common.init_session_state()
common.sidebar()


# Title of the app
st.title('ELASTICSEARCH')

# Function to initialize the MongoDB connection
def get_mongo_client():
    url = st.secrets["mongo_db"]["url"]
    return pymongo.MongoClient(url)


# Function to search for vCons in Elasticsearch
def search_vcons(query, es_client):
    
    # Get the list of elastic search indices, then search for the query
    elastic_indices = es_client.indices.get(index="*").keys()
    final_results = []
    for index in elastic_indices:            
        body = {
            "query": {
                "multi_match": {
                    "query": query
                }
            }
        }
        results = es_client.search(index=index, body=body)
        final_results.append(results)
    return final_results
       
# Function to display the search results
def display_results(final_results):
    for result in final_results:
        if result.get('hits', {}).get('total', {}).get('value', 0) > 0:
            for hit in result.get('hits', {}).get('hits', []):
                st.write("From index :", hit.get('_index'))
                st.write("ID :", hit.get('_id'))
                st.write("Source :", hit.get('_source'))
                st.divider()
                
    
# Search for vCons
search_query = st.text_input("SEARCH VCONS")
if st.button("SEARCH"):
    es_client = get_es_client()
    results = search_vcons(search_query, es_client)
    display_results(results)
    