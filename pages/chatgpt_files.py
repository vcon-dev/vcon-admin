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
default_vector_store_name = st.secrets["openai"]["vector_store_name"]
vector_store_name = st.text_input("Vector Store Name", value=default_vector_store_name)

# Upload the vCons
upload = st.button("Upload")
if upload:
    vcons = common.get_vcons()
    files = []
    progress_text = f"Uploading {len(vcons)} files to OpenAI."
    with st.progress(0, text=progress_text):
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
        st.progress((i+1)/len(vcons))
    st.success("Files uploaded successfully")
      

    progress_text = "Deleting old vector store if it exists"
    with st.progress(0, text=progress_text):
      vector_store = client.beta.vector_stores.list()
      for store in vector_store.data:
        if store.name == st.secrets["openai"]["vector_store_name"]:
          st.write(f"Deleting vector store {store.id}")
          client.beta.vector_stores.delete(vector_store_id=store.id)
          
    progress_text = "Creating new vector store"
    with st.progress(0, text=progress_text):
      vector_store = client.beta.vector_stores.create(
        name=vector_store_name
      )    
           
    progress_text = "Adding files to the vector store"
    with st.progress(0, text=progress_text):
      for file in files:
        vector_store_file = client.beta.vector_stores.files.create(
          vector_store_id=vector_store.id,
          file_id=file.id
        )

    st.success("Files uploaded successfully and added to the vector store")
    
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

