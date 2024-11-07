import streamlit as st
import lib.common as common
import os
import json
from datetime import datetime
from openai import OpenAI
import time

client = OpenAI(
    organization=st.secrets["openai"]["organization"],
    project=st.secrets["openai"]["project"],
    api_key=st.secrets["openai"]["testing_key"],
)

default_model = st.secrets["openai"].get("model", "gpt-4o-mini")
common.init_session_state()
common.sidebar()

# Synchronize the vCons into Open AI
st.title("OpenAI")


# Make a tab group for the different actions
tabs = ["Upload Files", "Download Files", "Delete Files", "List Files"]
upload, download, delete, list_files = st.tabs(tabs)

with upload:
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
    
    # If there are no vector stores, create one
    if not vector_stores.data:
        st.write("No vector stores found. Creating one.")
        vector_store = client.beta.vector_stores.create(name="vcons")
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
                    vector_store_id=vector_store_id, file_id=file.id
                )
            st.write(f"Files added to vector store {vector_store_id}")
            st.write(f"Files uploaded to OpenAI.")

with download:
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

with delete:
    "This will delete all the files in the selected purpose. Be careful, as this action cannot be undone."

    delete_files = st.button("Delete Files from OpenAI")
    if delete_files:
        progress_text = "Deleting files from OpenAI."
        with st.progress(0, text=progress_text):
            files = client.files.list(purpose=purpose)
            for i, file in enumerate(files):
                client.files.delete(file_id=file.id)
                st.progress((i + 1) / len(files))
        st.success("Files deleted successfully")

with list_files:
    "List all of the files currently uploaded. This will show the file name and the file size."

    show_files = st.button("Fetch")
    if show_files:
        resp = client.files.list(purpose=purpose)
        files = resp.data
        st.metric("Number of Files", len(files))
        with st.expander("Details"):
            for file in files:
                st.write(
                    f"{file.filename} - {file.bytes} bytes - {datetime.fromtimestamp(file.created_at)}"
                )

st.divider()

"## Assistant Testing"

today = datetime.today().strftime("%Y-%m-%d")

# Make a list of the available assistants
assistants = client.beta.assistants.list()

# If there are no assistants, create one
if not assistants.data:
    st.write("No assistants found. Creating one.")
    assistant = client.beta.assistants.create(name="assistant", model=default_model)
    assistants = client.beta.assistants.list()

# Use the human readable name for the dropdown
assistant_names = [assistant.name for assistant in assistants.data]
assistant_name = st.selectbox("Assistant", assistant_names)

# Show the assistant details. Get the assistant by name
assistant = assistants.data[assistant_names.index(assistant_name)]
with st.expander("Assistant Details"):
    # Make a human readable date
    created_at = datetime.fromtimestamp(assistant.created_at)
    st.write(f"**Name**: {assistant.name}")
    st.write(f"**ID**: {assistant.id}")
    st.write(f"**Model**: {assistant.model}")
    st.write(f"**Instructions**: {assistant.instructions}")
    st.write(f"*Description**: {assistant.description}")
    st.write(f"**Tools**: {assistant.tools}")
    st.write(f"**Created At**: {created_at}")


with st.spinner("Connecting to OpenAI..."):
    # Create a new thread if one does not exist
    if "thread" not in st.session_state:
        st.session_state.thread = client.beta.threads.create()
        st.session_state.messages = []
        st.session_state.vcons = []
        st.session_state.uploaded_files = []

        message = client.beta.threads.messages.create(
            thread_id=st.session_state.thread.id,
            role="user",
            content="Today is " + today,
        )


# In the sidebar, show the vConIDs that are used in this conversation,
# and provide a link to the vCon detail page using the vConID and CONV_DETAIL_URL
# Get the thread
thread = client.beta.threads.retrieve(thread_id=st.session_state.thread.id)


# Add the new messages to the chat
messages = st.session_state.messages
for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("How can I help you?"):
    # Add the message to the chat
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    message = client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=prompt
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id, assistant_id=assistant.id
    )

    # Wait for the run to complete
    # Show a progress bar while waiting
    status_bar = st.status("Processing...")
    with status_bar:
        status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        while status.status != "completed":
            time.sleep(1)  # Add a 1-second delay between status retrievals
            status = client.beta.threads.runs.retrieve(
                thread_id=thread.id, run_id=run.id
            )

    # Print out the run step object
    steps = client.beta.threads.runs.steps.list(thread_id=thread.id, run_id=run.id)
    for step in steps:
        step_details = step.step_details
        if step_details.type == "message_creation":
            message_id = step.step_details.message_creation.message_id
            message = client.beta.threads.messages.retrieve(
                thread_id=thread.id, message_id=message_id
            )
            message_content = message.content[0].text
            with st.chat_message("assistant"):
                st.markdown(message_content.value)
            st.session_state.messages.append(
                {"role": "assistant", "content": message_content.value}
            )
