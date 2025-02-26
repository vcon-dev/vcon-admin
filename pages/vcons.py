import streamlit as st
import pandas as pd
import lib.common as common
from vcon import Vcon

common.init_session_state()
common.sidebar()

def parties_as_markdown(parties):
    party_strings = []
    if not parties:
        return ""
        
    for party in parties:
        # Handle Party objects from the vcon library
        try:
            # Access properties directly as attributes
            role = ""
            if hasattr(party, "meta") and party.meta and "role" in party.meta:
                role = party.meta["role"].upper()
                
            name = getattr(party, "name", "")
            tel = getattr(party, "tel", "")
            email = getattr(party, "mailto", "")
            
            party_strings.append(f"{role} - {name} {tel} {email}".strip())
        except Exception as e:
            # Fallback to string representation
            party_strings.append(str(party))
                
    return " | ".join(party_strings)

def limit_to_words(text, word_limit=100):
    """Limit text to a specified number of words and add ellipsis if truncated."""
    if not text:
        return ""
    words = text.split()
    if len(words) <= word_limit:
        return text
    return " ".join(words[:word_limit]) + "..."

try:
    # Get vCon count using the centralized MongoDB connection
    vcon_count = common.count_vcons()
except Exception as e:
    st.error(f"Unable to connect to mongo database: {str(e)}")
    st.stop()

if vcon_count == 0:
    st.error("No VCONs found in the database")
    st.stop()

st.title(f"VCON INFO: {vcon_count} vcons")

# Pagination settings and controls
if "items_per_page" not in st.session_state:
    st.session_state.items_per_page = 25

# Dropdown for selecting number of rows
items_per_page_options = [10, 25, 50, 100]

# Streamlit session state to keep track of the current page
if "page" not in st.session_state:
    st.session_state.page = 0

# Pagination controls
total_pages = (vcon_count + st.session_state.items_per_page - 1) // st.session_state.items_per_page
skip = st.session_state.page * st.session_state.items_per_page

# Fetch documents using the common MongoDB connection
vcon_docs = common.get_vcons(
    limit=st.session_state.items_per_page,
    sort_by="created_at",
    sort_order="descending"
)

# Convert MongoDB documents to Vcon objects
vcons = [Vcon(vcon_doc) for vcon_doc in vcon_docs]

# Create list of dictionaries for DataFrame
vcon_data = []
for vcon in vcons:
    # First try to get summary, then fall back to transcript
    content = ""
    
    # Try to get summary first
    summary_analysis = vcon.find_analysis_by_type("summary")
    if summary_analysis and "body" in summary_analysis:
        if isinstance(summary_analysis["body"], str):
            content = summary_analysis["body"]
        elif isinstance(summary_analysis["body"], dict) and "summary" in summary_analysis["body"]:
            content = summary_analysis["body"]["summary"]
        else:
            content = str(summary_analysis["body"])
    
    # If no summary, fall back to transcript
    if not content:
        transcript_analysis = vcon.find_analysis_by_type("transcript")
        if transcript_analysis and "body" in transcript_analysis:
            # Use deepgram_transcript_to_markdown if body is a dictionary with the expected structure
            if isinstance(transcript_analysis["body"], dict):
                try:
                    content = common.deepgram_transcript_to_markdown(transcript_analysis["body"])
                except Exception as e:
                    # Fallback to string representation if the structure doesn't match
                    content = str(transcript_analysis["body"])
            elif isinstance(transcript_analysis["body"], str):
                content = " ".join(transcript_analysis["body"].split())
            else:
                # Handle non-string body content
                content = str(transcript_analysis["body"])
    
    # Limit content to 100 words
    content = limit_to_words(content, 100)
    
    vcon_dict = {
        "created_at": vcon.created_at,
        "party_names": parties_as_markdown(vcon.parties),
        "uuid": vcon.uuid,
        "content": content
    }
    vcon_data.append(vcon_dict)

# Create and clean DataFrame
df = pd.DataFrame(vcon_data)

# Process DataFrame
inspect_path = st.secrets["inspect_path"] if "inspect_path" in st.secrets else "http://localhost:8501/inspect"

if not df.empty:
    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime('%Y-%m-%d %H:%M')
    df["link"] = df["uuid"].apply(lambda x: f'<a href="{inspect_path}?uuid={x}">Details</a>')

    # Change the column order
    df = df[["uuid", "created_at", "party_names", "content", "link"]]

    # Change the column names
    df.columns = [ "UUID",  "Created", "Parties", "Content","Link"]

# Display DataFrame
st.markdown(df.to_html(escape=False), unsafe_allow_html=True)

# Create 4 columns for the pagination controls and dropdown
col0, col1, col2, col3, col4, col5 = st.columns([4, 1, 1, 1, 1, 4])

with col1:
    if st.button("Previous") and st.session_state.page > 0:
        st.session_state.page -= 1
with col2:
    st.write(f"Page {st.session_state.page + 1} of {total_pages}")
with col3:
    if st.button("Next") and st.session_state.page < total_pages - 1:
        st.session_state.page += 1
with col4:
    st.selectbox(
        "Rows:",
        options=items_per_page_options,
        index=items_per_page_options.index(st.session_state.items_per_page),
        key="items_per_page",
        label_visibility="collapsed"
    )
