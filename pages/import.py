import streamlit as st
import pymongo
import json
import redis
import boto3
import zipfile
import io
import lib.common as common

common.init_session_state()
common.sidebar()


# Initialize connection.
# Uses st.cache_resource to only run once.
@st.cache_resource
def init_connection():
    url = st.secrets["mongo_db"]["url"]
    return pymongo.MongoClient(url)

@st.cache(allow_output_mutation=True)
def load_and_insert_file(file):
    try:
        document = json.load(file)
        collection.replace_one({'_id': document['uuid']}, document, upsert=True)
    except json.JSONDecodeError as e:
        st.warning(f"SKIPPED INVALID JSON, FILE {filename}")
        return False
    return True


client = init_connection()

st.title("IMPORT VCONS")

tab_names= ["UPLOAD ONE", "UPLOAD ZIP", "UPLOAD JSONL", "URL", "TEXT", "REDIS", "S3"]
upload_tab, upload_zip_tab, jsonl_tab, url_tab, text_tab, redis_tab, s3_tab = st.tabs(tab_names)

with upload_tab:
    "**UPLOAD A SINGLE VCON FILE**"
    # Allow the user to upload a single JSON file
    uploaded_files = st.file_uploader("UPLOAD", type=["json", "vcon"], accept_multiple_files=True)
    if uploaded_files is not None:
        if st.button("UPLOAD AND INSERT"):
            db = client[st.secrets["mongo_db"]['db']]
            collection = db[st.secrets["mongo_db"]['collection']]
            for uploaded_file in uploaded_files:
                try:
                    document = json.load(uploaded_file)
                    collection.replace_one({'_id': document['uuid']}, document, upsert=True)
                    st.success("INSERTED SUCCESSFULLY!")
                except json.JSONDecodeError as e:
                    st.warning("INVALID JSON")
                    st.error(e)

with upload_zip_tab:
    "**UPLOAD ZIP FILE**"
    # Allow the user to upload a zip file
    uploaded_file = st.file_uploader("UPLOAD ZIP", type="zip")
    if uploaded_file is not None:
        if st.button("UPLOAD AND INSERT", key="upload_zip"):
            db = client[st.secrets["mongo_db"]['db']]
            collection = db[st.secrets["mongo_db"]['collection']]
            z = zipfile.ZipFile(io.BytesIO(uploaded_file.read()))
            vcons_uploaded = 0
            
            for filename in z.namelist():
                # If this ends in .vcon or .json, we'll try to load it
                if not filename.endswith("/"):
                    with z.open(filename) as file:
                        try:
                            # load the file from the zip
                            document = json.load(file)
                            collection.replace_one({'_id': document['uuid']}, document, upsert=True)
                            vcons_uploaded += 1
                        except json.JSONDecodeError as e:
                            continue
                        except UnicodeDecodeError as e:
                            continue
            st.success(f"INSERTED {vcons_uploaded} SUCCESSFULLY!")
   


with jsonl_tab:
    "**UPLOAD BULK VCON**"

    uploaded_file = st.file_uploader("UPLOAD JSONL", type="jsonl, vconl")

    if uploaded_file is not None:
        if st.button("UPLOAD AND INSERT"):
            db = client[st.secrets["mongo_db"]['db']]
            collection = db[st.secrets["mongo_db"]['collection']]
            for i, line in enumerate(uploaded_file):
                try:
                    document = json.loads(line)
                    collection.replace_one({'_id': document['uuid']}, document, upsert=True)
                except json.JSONDecodeError as e:
                    st.warning(f"SKIPPED INVALID JSON, INDEX {i}")
                    continue
            st.success("INSERTED SUCCESSFULLY!")

with url_tab:
    # Import from a URL
    "**IMPORT FROM URL**"
    url = st.text_input("ENTER URL")
    if url:
        if st.button("IMPORT", key="import_url"):
            db = client[st.secrets["mongo_db"]['db']]
            collection = db[st.secrets["mongo_db"]['collection']]
            try:
                document = json.load(url)
                collection.replace_one({'_id': document['uuid']}, document, upsert=True)
                st.success("INSERTED SUCCESSFULLY!")
            except json.JSONDecodeError as e:
                st.warning("INVALID JSON")
                st.error(e)

with text_tab:
    # Import from a URL
    "**IMPORT FROM TEXT**"
    text = st.text_area("ENTER TEXT")
    if text:
        if st.button("IMPORT", key="import_text"):
            db = client[st.secrets["mongo_db"]['db']]
            collection = db[st.secrets["mongo_db"]['collection']]
            try:
                document = json.loads(text)
                collection.replace_one({'_id': document['uuid']}, document, upsert=True)
                st.success("INSERTED SUCCESSFULLY!")
            except json.JSONDecodeError as e:
                st.warning("INVALID JSON")
                st.error(e)

with redis_tab:
    # Import from REDIS
    "**IMPORT FROM REDIS**"
    redis_url= st.text_input("ENTER REDIS URL")
    redis_password = st.text_input("ENTER REDIS PASSWORD")
    if redis_url:
        if st.button("IMPORT", key="import_redis"):
            db = client[st.secrets["mongo_db"]['db']]
            collection = db[st.secrets["mongo_db"]['collection']]

            # Connect to the REDIS server, and find all the keys with the pattern "vcon:*"
            if redis_password:
                redis_client = redis.Redis.from_url(redis_url, password=redis_password)
            else:
                redis_client = redis.Redis.from_url(redis_url)
            keys = redis_client.keys("vcon:*")
            with st.spinner("IMPORTING VCONS"):
                for key in keys:
                    vcon = redis_client.json().get(key)
                    try:
                        collection.replace_one({'_id': vcon['uuid']}, vcon, upsert=True)
                    except json.JSONDecodeError as e:
                        st.warning("INVALID JSON")
                        st.error(e)
            st.success("IMPORTED SUCCESSFULLY!")

with s3_tab:
    "**IMPORT S3 BUCKET**"
    # For inputs, use the 
    AWS_ACCESS_KEY_ID = st.secrets['aws']["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = st.secrets['aws']["AWS_SECRET_ACCESS_KEY"]
    AWS_DEFAULT_REGION = st.secrets['aws']["AWS_DEFAULT_REGION"]
    s3_bucket = st.text_input("ENTER S3 BUCKET")
    s3_path = st.text_input("ENTER S3 PATH")
    if s3_bucket:
        if st.button("IMPORT", key="import_s3"):
            db = client[st.secrets["mongo_db"]['db']]
            collection = db[st.secrets["mongo_db"]['collection']]
            s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_DEFAULT_REGION)

            # Connect to the S3 bucket and find all the keys with the pattern "vcon:*"
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=s3_bucket, Prefix=s3_path)

            # Count the number of vCons we're importing overall, so we can show a progress bar
            total_vcons = 0
            for page in pages:
                # Check to see if there are any vCons in this page
                key_count = page['KeyCount']
                if key_count == 0:
                    st.warning("NO VCONS FOUND")
                    st.stop()
                    break
                for obj in page['Contents']:
                    key = obj['Key']
                    if key.endswith(".vcon.json") or key.endswith(".vcon"):
                        total_vcons += 1
                        
            # Reset the paginator
            pages = paginator.paginate(Bucket=s3_bucket, Prefix=s3_path)
            progress_text = f"IMPORTING {total_vcons} VCONS"
            progress_bar = st.progress(0, text=progress_text)
            skipped_files = 0
            uploaded_files = 0
            for index, page in enumerate(pages):
                for obj in page['Contents']:
                    key = obj['Key']
                    if key.endswith(".vcon.json") or key.endswith(".vcon"):
                        try:
                            vcon = s3_client.get_object(Bucket=s3_bucket, Key=key)
                            vcon = json.loads(vcon['Body'].read())
                            result = collection.replace_one({'_id': vcon['uuid']}, vcon, upsert=True)
                            uploaded_files += 1
                        except json.JSONDecodeError as e:
                            st.warning("INVALID JSON")
                            skipped_files += 1
                        except UnicodeDecodeError as e:
                            st.warning("INVALID JSON")
                            skipped_files += 1
                        except Exception as e:
                            st.warning("INVALID JSON")
                            skipped_files += 1
                    else:
                        skipped_files += 1
                    # Calculate the percentage of vCons uploaded, maximum 100%
                    percentage_done = min(100, int((uploaded_files) / total_vcons * 100))
                    
                    progress_bar.progress(percentage_done, f"{uploaded_files} UPLOADED, {skipped_files} SKIPPED")
                        
            st.success(f"UPLOADED {uploaded_files}, SKIPPED: {skipped_files}")