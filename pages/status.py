import streamlit as st
from streamlit_extras.streaming_write import write
import lib.common as common

common.init_session_state()
common.authenticate()
common.sidebar()

# Show the status of the system.
import docker

client = docker.from_env()
containers = client.containers.list()


col1, col2 =  st.columns([5, 5])
with col1:    
    "## RUNNING DOCKER CONTAINERS"
    
    for container in containers:
        with st.expander(container.name):
            f"#### {container.name}"
            f"Status: {container.status}"
            f"ID: {container.id}"
            f"Image: {container.image.tags}"
            f"Command: {container.attrs['Config']['Cmd']}"
            f"Created: {container.attrs['Created']}"
            f"Ports: {container.attrs['NetworkSettings']['Ports']}"
            
            # Show the container logs
            if st.button(f"SHOW LOGS FOR {container.name}"):
                for line in container.logs(tail=10, follow=True, stream=True):
                    # Show the logs in streamlit as they come in
                    st.write(line.decode('utf-8'))                    
    
with col2:
    "## SYSTEM STATUS"

    with st.expander("SESSION STATE"):
        st.json(st.session_state)
    with st.expander("SECRETS"):
        st.write(st.secrets)
    with st.expander("MONGO"):        
        # Validate the connection to the MongoDB database
        client = common.get_mongo_client()
        db = client[st.secrets["mongo_db"]["db"]]
        collection = db[st.secrets["mongo_db"]["collection"]]
        vcon_count = collection.count_documents({})
        # Get status of the MongoDB database
        st.header(f"MONGODB INFO")
        st.write(f"Database: {st.secrets['mongo_db']['db']}")
        st.write(f"Collection: {st.secrets['mongo_db']['collection']}")
        st.write(f"URL: {st.secrets['mongo_db']['url']}")
        st.write(f"VCON Count: {vcon_count}")
                
    with st.expander("ELASTICSEARCH"):
        # Validate the connection to the Elasticsearch database
        es_client = common.get_es_client()
        es_info = es_client.info()
        st.header(f"ELASTICSEARCH INFO")
        st.write(es_info.raw)
