import streamlit as st
from streamlit import column_config
import lib.common as common
from vcon import Vcon
import json
import pandas as pd
from datetime import datetime

common.init_session_state()
common.sidebar()

# Initialize variables that will be used outside the status block
vcons = []
table_data = []
df = None
display_df = None



# Add filter options
col1, col2, col3 = st.columns([6, 3, 3])

with col1:
    # Title and page layout
    st.title("vCon Manager")

with col3:
    limit = st.number_input("Number of vCons to display", min_value=10, max_value=1000, value=100, step=10)
    sort_options = {
        "Created (newest first)": {"field": "created_at", "order": "descending"},
        "Created (oldest first)": {"field": "created_at", "order": "ascending"},
        "Updated (newest first)": {"field": "updated_at", "order": "descending"},
        "Updated (oldest first)": {"field": "updated_at", "order": "ascending"}
    }
    sort_selection = st.selectbox("Sort by", options=list(sort_options.keys()))

    # Get the selected sort option
    sort_config = sort_options[sort_selection]


with col1:
    # Create a status container for feedback
    status_container = st.empty()

    # Start the data loading process with status feedback
    with status_container.status("Starting vCon retrieval process...") as status:
        status.update(label="Querying MongoDB for vCons...", state="running")
        
        # Fetch vCons using the optimized common module function - note the include_full_dialog=False parameter
        # This prevents loading large wav files in the dialog, significantly improving performance
        vcons = common.get_vcons(
            limit=limit, 
            sort_by=sort_config["field"], 
            sort_order=sort_config["order"],
            include_full_dialog=False  # Only fetch metadata, not the large dialog body content
        )
        
        if not vcons:
            status.update(label="No vCons found in database", state="complete")
            st.stop()
            
        # Update status for data processing
        status.update(label=f"Retrieved {len(vcons)} vCons from MongoDB. Processing data...", state="running")
        
        # Prepare data for the table
        table_data = []
        
        # Create a progress bar for processing vCons
        progress_bar = st.progress(0)
        total_vcons_to_process = len(vcons)
        
        for idx, vcon in enumerate(vcons):
            # Update progress
            progress_value = int((idx + 1) / total_vcons_to_process * 100)
            progress_bar.progress(progress_value, text=f"Processing vCon {idx + 1} of {total_vcons_to_process}")
            
            # Format dates nicely
            created_at = vcon.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    created_at = str(created_at)
                                
            # Count dialog entries - we still have dialog metadata, just not the body content
            dialog_count = len(vcon.get('dialog', []))
            
            # Get parties information
            parties = vcon.get('parties', [])
            parties_str = ", ".join([p.get('name', 'Unknown') for p in parties]) if parties else "No parties"
            if len(parties_str) > 50:
                parties_str = parties_str[:50] + "..."
            
            # Add estimated size information
            dialog_types = {}
            for dialog in vcon.get('dialog', []):
                mime_type = dialog.get('mime_type', 'unknown')
                dialog_types[mime_type] = dialog_types.get(mime_type, 0) + 1
            
            # Format dialog types as a string
            dialog_types_str = ", ".join([f"{count} {mime}" for mime, count in dialog_types.items()])
            
            # Get the UUID for this vCon
            uuid = vcon.get('uuid', 'N/A')
            
            # Add to table data
            table_data.append({
                "Created At": created_at or "N/A",
                "Parties": parties_str,
                "Dialog Entries": dialog_count,
                "Dialog Types": dialog_types_str,
                "Details": f"inspect?vcon_uuid={uuid}"  # HTML link
            })
        
        # Clear the progress bar after processing
        progress_bar.empty()
        
        # Update status for table creation
        status.update(label="Creating and formatting display table...", state="running")
        
        # Create DataFrame
        df = pd.DataFrame(table_data)
        
        # Create a display version of the dataframe without the UUID column (but we'll keep it in the df for reference)
        display_cols = [col for col in df.columns if col != "UUID"]
        display_df = df[display_cols]
            
        # Update status to complete
        status.update(label=f"Successfully loaded and processed {len(vcons)} vCons", state="complete")

# Configure the dataframe with column settings
column_config = {
    "Created At": column_config.DatetimeColumn(
        "Created At",
        help="When the vCon was created",
    ),
    "Dialog Entries": column_config.NumberColumn(
        "Dialog Entries",
        help="Number of dialog entries",
    ),
    "Details": st.column_config.LinkColumn(  # Changed to LinkColumn
        "Details",
        help="Click to view vCon details",
        width="small",
        validate="^<a.*>.*</a>$",
        display_text="View"
    )
}

# Display the dataframe
st.data_editor(
    display_df,
    column_config=column_config,
    hide_index=True,
    disabled=["Created At", "Parties", "Dialog Entries", "Dialog Types"],
)
# 