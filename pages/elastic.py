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

common.init_session_state()
common.sidebar()

# Title of the app
st.title('ELASTICSEARCH')

# Function to initialize the MongoDB connection
def get_mongo_client():
    url = st.secrets["mongo_db"]["url"]
    return pymongo.MongoClient(url)

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


# Function to return the summary of a vCon if it's available
def get_vcon_summary(vcon):
    if vcon:
        analysis = vcon.get('analysis', [])
        for a in analysis:
            if a.get('type') == 'summary':
                return a.get('body')
    return None

# Function to return the transcript of a vCon if it's available
def get_vcon_transcript(vcon):
    if vcon:
        analysis = vcon.get('analysis', [])
        for a in analysis:
            if a.get('type') == 'transcript':
                return a.get('body')
    return None

# Function to index a vCon in Elasticsearch
def index_vcon(vcon, es_client):
    if vcon:
        vcon_id = vcon.get('uuid')
        if vcon_id:
            body = {
                "uuid": vcon_id,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "parties": vcon.get('parties', []),
                "dialog": vcon.get('dialog', []),
                "analysis": vcon.get('analysis', []),
                "attachments": vcon.get('attachments', []),
                "summary": get_vcon_summary(vcon),
                "transcript": get_vcon_transcript(vcon)
            }
            es_client.index(index="vcons", id=vcon_id, body=body)
            return True
    return False

# Function to index all vCons in the MongoDB collection
def index_all_vcons(es_client):
    client = get_mongo_client()
    db = client[st.secrets["mongo_db"]["db"]]
    collection = db[st.secrets["mongo_db"]["collection"]]
    vcons = collection.find({})
    for vcon in vcons:
        try:
            index_vcon(vcon, es_client)
        except Exception as e:
            print(e)
            continue
    return True

# Function to search for vCons in Elasticsearch
def search_vcons(query, es_client):
    body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["parties.name", "dialog.text", "analysis.body", "summary", "transcript", "attachments.name"]
            }
        }
    }
    results = es_client.search(index="vcons", body=body)
    return results

# Function to display the search results
def display_results(results):
    hits = results.get('hits', {}).get('hits', [])
    for hit in hits:
        source = hit.get('_source', {})
        parties = source.get('parties', [])
        dialog = source.get('dialog', [])
        analysis = source.get('analysis', [])
        st.write(f"## {source.get('uuid')}")
        st.write("### PARTIES")
        for party in parties:
            st.write(f"- {party.get('name')}")
        st.write("### DIALOG")
        for turn in dialog:
            st.write(f"- {turn.get('speaker')}: {turn.get('text')}")
        st.write("### ANALYSIS")
        for a in analysis:
            st.write(f"- {a.get('type')}: {a.get('body')}")

# Upload the vCons to Elasticsearch
if st.button("UPLOAD VCONS TO ELASTICSEARCH"):
    es_client = get_es_client()
    if index_all_vcons(es_client):
        st.success("VCONS UPLOADED SUCCESSFULLY!")
    else:
        st.error("ERROR UPLOADING VCONS!")

# Search for vCons
search_query = st.text_input("SEARCH VCONS")
if st.button("SEARCH"):
    es_client = get_es_client()
    results = search_vcons(search_query, es_client)
    display_results(results)
    