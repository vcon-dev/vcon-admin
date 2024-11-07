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
    # {"tel": "+19981076214", "meta": {"role": "customer"}, "name": "Janet Davis", "email": "janet.davis@gmail.com"}
    # Convert the party to a markdown string, including all of the information,
    # yet checking to make sure it exists
    party_str = ""
    for party in parties:
        role = party.get("meta", {}).get("role", "")
        # Upper case the role
        role = role.upper()
        party_str += f"{role} - {party.get('name', '')} {party.get('tel', '')} {party.get('email', '')}"
    return party_str


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

vcons = collection.find({})

st.title(f"VCON INFO: {vcon_count} vcons")

# Pagination settings
items_per_page = 10

# Streamlit session state to keep track of the current page
if "page" not in st.session_state:
    st.session_state.page = 0

# Pagination controls
total_items = collection.count_documents({})
total_pages = (total_items + items_per_page - 1) // items_per_page

# Fetch and display documents for the current page
skip = st.session_state.page * items_per_page
documents = list(collection.find().skip(skip).limit(items_per_page))
df = pd.DataFrame(documents)

# Remove the analysis column
to_remove = ["analysis", "attachments", "updated_at", "_id", "vcon"]
for col in to_remove:
    if col in df.columns:
        # Check to see if the column exists
        if col in df.columns:
            df = df.drop(columns=col)

# Convert the created_at column to a datetime object
df["created_at"] = df["created_at"].apply(lambda x: pd.to_datetime(x))

# Extract the from each dialog object the total duration
df["total_duration"] = df["dialog"].apply(
    lambda x: sum([int(dialog.get("duration", 0)) for dialog in x])
)

# Extract the names, tel and email addresses from parties
df["party_names"] = df["parties"].apply(lambda x: parties_as_markdown(x))

# Count the number of dialogs in each vcon
df["dialog_count"] = df["dialog"].apply(lambda x: len(x))

df["link"] = df["uuid"].apply(lambda x: f'<a href="/inspect?uuid={x}">Details</a>')

df = df.drop(columns=["parties"])
df = df.drop(columns=["dialog"])

optional_columns = ["redacted", "group", "appended"]
# If the column exists, remove it
for col in optional_columns:
    if col in df.columns:
        df = df.drop(columns=col)


# Display dataframe with clickable links
st.markdown(df.to_html(escape=False), unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Previous") and st.session_state.page > 0:
        st.session_state.page -= 1
with col2:
    st.write(f"Page {st.session_state.page + 1} of {total_pages}")

with col3:
    if st.button("Next") and st.session_state.page < total_pages - 1:
        st.session_state.page += 1
