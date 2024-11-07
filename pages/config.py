import streamlit as st
from streamlit_extras.streaming_write import write
import lib.common as common

common.init_session_state()
common.sidebar()

# Show the status of the system.
import docker

"## CONSERVER CONFIGURATION"

        
config = common.get_conserver_config()
st.json(config)
