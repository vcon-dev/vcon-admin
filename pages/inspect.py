import streamlit as st
import json
import lib.common as common
import pickle

common.init_session_state()
common.sidebar()

# Title and page layout
st.title("VCON INSPECTOR")

# Function to return the summary of a vCon if it's available
def get_vcon_summary(vcon):
    if vcon:
        analysis = vcon.get('analysis', [])
        for a in analysis:
            if a.get('type') == 'summary':
                return a.get('body')
    return None

# Get the vCon ID from session state and clear it to prevent continuous redirection
initial_vcon = st.session_state.get('selected_vcon', '')
if 'selected_vcon' in st.session_state:
    del st.session_state.selected_vcon
    
# Check the query params for a vcon id, if it exists, use it as the initial vcon id
if 'vcon_uuid' in st.query_params:
    initial_vcon = st.query_params['vcon_uuid']

selected_vcon = st.text_input("ENTER A VCON ID", value=initial_vcon)

if selected_vcon:
    st.session_state.selected_vcon = selected_vcon

    # Using the common module function instead of direct connection
    vcon = common.get_vcon(selected_vcon)

    # ADD A BUTTON FOR DOWNLOADING THE VCON as JSON
        
    serialized_data = pickle.dumps(vcon)
    download = st.download_button(
        label="DOWNLOAD VCON",
        data=serialized_data,
        file_name=f"{selected_vcon}.json",
        mime="application/json"
    )

    # ADD A BUTTON FOR ADDING THE UUID TO THE WORKBENCH
    if st.button("ADD TO INPUTS"):
        if 'vcon_uuids' not in st.session_state:
            st.session_state.vcon_uuids = []
        vcon_uuids = st.session_state.vcon_uuids
        vcon_uuids.append(selected_vcon)
        st.session_state.vcon_uuids = vcon_uuids
        st.success(f"ADDED {selected_vcon} TO WORKBENCH.")

    if vcon:
        try:
            created_at = vcon['created_at']
            updated_at = vcon.get("updated_at", "vCon has not been updated")

            # Make sure we don't throw errors here.
            parties = vcon.get("parties", [])
            dialog = vcon.get("dialog", [])
            attachments = vcon.get("attachments", [])
            analysis = vcon.get("analysis", [])

            # Display the summary of the vCon
            summary = get_vcon_summary(vcon)
            if summary:
                st.header("Summary")
                st.write(summary)

            # Create tabs for different sections
            tabs = st.tabs(['COMPLETE', 'ANALYSIS', 'DIALOG', 'PARTIES', 'ATTACHMENTS'])

            # Display content in respective tabs
            with tabs[1]:
                if analysis:
                    st.json(analysis)

            with tabs[2]:
                if dialog:
                    st.json(dialog)

            with tabs[3]:
                if parties:
                    st.json(parties)

            with tabs[4]:
                if attachments:
                    st.json(attachments)

            with tabs[0]:
                st.json(vcon)

        except KeyError:
            st.error("Invalid vCon, both created_at and uuid are required.")
    else:
        st.error(f"No vCon found with uuid: {selected_vcon}")