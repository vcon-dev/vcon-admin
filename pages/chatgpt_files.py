import streamlit as st
import lib.common as common
import os
import json
from datetime import datetime

from openai import OpenAI

client = OpenAI(
  organization=st.secrets["openai"]["organization"],
  project=st.secrets["openai"]["project"],
  api_key=st.secrets["openai"]["testing_key"]
)
common.init_session_state()
common.sidebar()

# Synchronize the vCons into Open AI
st.title("OpenAI File Synchronization")

st.divider()
st.subheader("Upload Files")

"Upload the vCons to OpenAI. You can choose the purpose of the files, such as 'assistants', 'batch', 'fine-tune', etc."

file_purposes = [
    "assistants",
    "assistants_output",
    "batch",
    "batch_output",
    "fine-tune",
    "fine-tune-results",
]
purpose = st.selectbox("File Purpose", file_purposes)

# Make a dropdown for the vector store. Use the API to get the vector stores, and then populate the dropdown
vector_stores = client.beta.vector_stores.list()

# Use the human readable name for the dropdown
vector_store_names = [vector_store.name for vector_store in vector_stores.data]
vector_store_id = st.selectbox("Vector Store", vector_store_names)

# Convert the human readable name to the ID
vector_store_id = vector_stores.data[vector_store_names.index(vector_store_id)].id
with st.expander("Vector Store Details"):
    vector_store = client.beta.vector_stores.retrieve(vector_store_id)
    st.write(f"**Name**: {vector_store.name}")
    st.write(f"**File Counts**:")
    st.write(f"  _In Progress_: {vector_store.file_counts.in_progress}")
    st.write(f"  _Completed_: {vector_store.file_counts.completed}")
    st.write(f"  _Failed_: {vector_store.file_counts.failed}")
    st.write(f"  _Cancelled_: {vector_store.file_counts.cancelled}")
    st.write(f"  **Total**: {vector_store.file_counts.total}")
    
    
# Upload the vCons
upload = st.button("Upload vCons to OpenAI")
if upload:
    vcons = common.get_vcons()
    files = []
    with st.status(f"Uploading vcons to vector store") as status:
      st.write(f"Uploading {len(vcons)} vcons to OpenAI.")
      for i, vcon in enumerate(vcons):
        # Save the vCon as a file
        file_name = f'{vcon["uuid"]}.vcon.json'
        with open(file_name, "w") as f:
            f.write(json.dumps(vcon))
            
        # Upload the file to OpenAI
        file = client.files.create(file=open(file_name, "rb"), purpose=purpose)
        files.append(file)      
        # Remove the file
        os.remove(file_name)
      st.write(f"Files uploaded to OpenAI.")
      st.write(f"Adding files to vector store")     
      for file in files:
        vector_store_file = client.beta.vector_stores.files.create(
          vector_store_id=vector_store_id,
          file_id=file.id
        )
      st.write(f"Files added to vector store {vector_store_id}")
      st.write(f"Files uploaded to OpenAI.")
    
st.divider()
st.subheader("Download Files")

"Download the files from OpenAI to your local machine."

# Download the vCons
download = st.button("Download")
if download:
  # Pick the destination folder
  st.write("Select the destination folder")
  destination = st.text_input("Destination", value=".")
  if not os.path.exists(destination):
      os.makedirs(destination)
  os.chdir(destination)
  
  st.write("Downloading files from OpenAI")
  with st.spinner("Downloading files from OpenAI"):
      files = client.files.list(purpose=purpose)
      for file in files:
          file_name = file["name"]
          with open(file_name, "wb") as f:
              f.write(file.get_content())
  st.success("Files downloaded successfully")
    
st.divider()
# Delete the files
st.subheader("Delete Files")

"This will delete all the files in the selected purpose. Be careful, as this action cannot be undone."


delete_files = st.button("Delete Files from OpenAI")
if delete_files:
  progress_text = "Deleting files from OpenAI."
  with st.progress(0, text=progress_text):
    files = client.files.list(purpose=purpose)
    for i, file in enumerate(files):
      client.files.delete(file_id=file.id)
      st.progress((i+1)/len(files))
  st.success("Files deleted successfully")
    
st.divider()
# List the files

st.subheader("Current Files")

"List all of the files currently uploaded. This will show the file name and the file size."

show_files = st.button("Fetch")
if show_files:
    resp = client.files.list(purpose=purpose)
    files = resp.data
    st.metric("Number of Files", len(files))
    with st.expander("Details"):
      for file in files:
          st.write(f"{file.filename} - {file.bytes} bytes - {datetime.fromtimestamp(file.created_at)}")

