import streamlit as st
import lib.common as common
from vcon import Vcon
import json
import pandas as pd
from datetime import datetime

common.init_session_state()
common.sidebar()

# Title and page layout
st.title("vCon Manager")

# Add filter options
col1, col2 = st.columns([1, 2])

with col1:
    limit = st.number_input("Number of vCons to display", min_value=10, max_value=1000, value=100, step=10)
    
with col2:
    sort_options = {
        "Created (newest first)": {"field": "created_at", "order": "descending"},
        "Created (oldest first)": {"field": "created_at", "order": "ascending"},
        "Updated (newest first)": {"field": "updated_at", "order": "descending"},
        "Updated (oldest first)": {"field": "updated_at", "order": "ascending"}
    }
    sort_selection = st.selectbox("Sort by", options=list(sort_options.keys()))

# Get the selected sort option
sort_config = sort_options[sort_selection]

# Display total count
total_vcons = common.count_vcons()
st.write(f"Total vCons in database: {total_vcons}")

# Add a status message about optimization
st.info("💡 Using optimized data loading (dialog content is loaded only when needed)")

# Initialize variables that will be used outside the status block
vcons = []
table_data = []
df = None
display_df = None

# Check if the UUID is in session state (from clicking a row)
if "selected_vcon" in st.session_state and st.session_state.selected_vcon:
    # Redirect to inspect page
    st.switch_page("pages/inspect_vcon.py")

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
    else:
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
                "UUID": uuid,
                "Created At": created_at or "N/A",
                "Parties": parties_str,
                "Dialog Entries": dialog_count,
                "Dialog Types": dialog_types_str,
                "Inspect": "View"  # Simple text that will be made clickable
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

# Display warnings or tables based on the data we loaded
if not vcons:
    st.warning("No vCons found in the database.")
else:
    # Make the table interactive with a callback for clicking on a row
    st.write("Click on 'View' in the Inspect column to view vCon details:")
    
    # Configure the dataframe with column settings
    column_config = {
        "Inspect": st.column_config.TextColumn(
            "Inspect",
            help="Click to view vCon details",
            width="small"
        )
    }
    
    # Display the dataframe with on_click handler
    selected_rows = st.dataframe(
        display_df, 
        use_container_width=True, 
        height=500,
        column_config=column_config,
        hide_index=True
    )
    
    # Handle clicking on a row in the dataframe
    if selected_rows.rows:
        # Get the index of the selected row
        selected_index = selected_rows.rows[0]
        # Get the UUID from the original dataframe using the selected index
        selected_uuid = df.iloc[selected_index]["UUID"]
        # Store the UUID in session state
        st.session_state.selected_vcon = selected_uuid
        # Redirect to the inspect page
        st.rerun()
    
    # Display summary statistics
    st.success(f"✅ Displaying {len(vcons)} vCons with a total of {sum(row['Dialog Entries'] for row in table_data)} dialog entries")

