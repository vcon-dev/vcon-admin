import streamlit as st
import pymongo
import lib.common as common
import pandas as pd

common.init_session_state()
common.sidebar()


# Function to initialize the MongoDB connection
def get_mongo_client():
    url = st.secrets["mongo_db"]["url"]
    return pymongo.MongoClient(url)


def parties_as_markdown(parties):
    party_strings = []
    for party in parties:
        role = party.get("meta", {}).get("role", "").upper()
        name = party.get("name", "")
        tel = party.get("tel", "")
        email = party.get("email", "")
        party_strings.append(f"{role} - {name} {tel} {email}".strip())
    return " | ".join(party_strings)


try:
    client = get_mongo_client()
    db = client[st.secrets["mongo_db"]["db"]]
    collection = db[st.secrets["mongo_db"]["collection"]]
    vcon_count = collection.count_documents({})
except pymongo.errors.ServerSelectionTimeoutError:
    st.error("Unable to connect to mongo database")
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

# Fetch documents with sorting
documents = list(collection.find()
                .sort("created_at", pymongo.DESCENDING)
                .skip(skip)
                .limit(st.session_state.items_per_page))

# Create and clean DataFrame
df = pd.DataFrame(documents)

# Process DataFrame
df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime('%Y-%m-%d %H:%M')
df["party_names"] = df["parties"].apply(parties_as_markdown)
df["link"] = df["uuid"].apply(lambda x: f'<a href="{st.secrets["inspect_path"]}?uuid={x}">Details</a>')
df["transcript"] = df["analysis"].apply(
    lambda analyses: next(
        (" ".join(analysis["body"].split()) for analysis in analyses if analysis.get("type") == "transcript" and "body" in analysis), ""
    )
)

# Change the column order
df = df[["created_at", "party_names", "link", "uuid", "transcript"]]

# Change the column names
df.columns = ["Created", "Parties", "Link", "UUID", "Transcript"]
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
