# Setup the session state for the app
import streamlit as st

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
