import streamlit as st
import lib.common as common
import json
import os
import logging
import time
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from openai import OpenAI
from datetime import datetime

# Initialize session state and sidebar - MUST be called before any other st commands
common.init_session_state()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("vcon_processing.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("milvus_vcon")

# Initialize OpenAI client for embeddings
@st.cache_resource
def get_openai_client():
    return OpenAI(
        organization=st.secrets["openai"]["organization"],
        project=st.secrets["openai"]["project"],
        api_key=st.secrets["openai"]["testing_key"],
    )

client = get_openai_client()

# After initialization, now we can add sidebar and title
common.sidebar()

st.title("Milvus Vector Store")
st.write("Load vCons from MongoDB into Milvus vector store for semantic search and retrieval.")

# Set up connection parameters for Milvus
milvus_host = st.secrets.get("milvus", {}).get("host", "localhost")
milvus_port = st.secrets.get("milvus", {}).get("port", "19530")

# Default embedding dimensions for OpenAI embeddings (text-embedding-3-small is 1536 dimensions)
EMBEDDING_DIM = 1536

# Connect to Milvus
try:
    connections.connect(host=milvus_host, port=milvus_port)
    st.success(f"Connected to Milvus at {milvus_host}:{milvus_port}")
except Exception as e:
    st.error(f"Failed to connect to Milvus: {e}")

# Create tabs for different operations
tabs = ["Create Collection", "Load vCons", "Search", "Delete Collection", "List Collections"]
create_tab, load_tab, search_tab, delete_tab, list_tab = st.tabs(tabs)

# Function to get embedding from OpenAI
@st.cache_data(ttl="1h", show_spinner=False)
def get_embedding(text):
    if not text:
        return [0] * EMBEDDING_DIM  # Return zero vector if text is empty
    
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# Function to extract text from vCon
@st.cache_data(ttl="1h", show_spinner=False)
def extract_text_from_vcon(vcon):# -> str | LiteralString | Any:
    start_time = time.time()
    vcon_id = vcon.get("uuid", "unknown")
    logger.info(f"Processing vCon {vcon_id}")
    
    text = ""
    extracted_components = []
    has_transcript = False
    has_summary = False
    
    # Extract transcript
    if "transcript" in vcon:
        transcript_length = len(vcon.get("transcript", []))
        text += " ".join([item.get("text", "") for item in vcon.get("transcript", []) if "text" in item]) + " "
        extracted_components.append(f"transcript ({transcript_length} entries)")
        logger.debug(f"Extracted transcript with {transcript_length} entries from vCon {vcon_id}")
        has_transcript = transcript_length > 0
    
    # Extract summary
    if "summary" in vcon and vcon["summary"]:
        text += vcon["summary"] + " "
        extracted_components.append("summary")
        logger.debug(f"Extracted summary from vCon {vcon_id}")
        has_summary = True
    
    # Extract party information
    party_count = 0
    if "parties" in vcon and vcon["parties"]:
        for party in vcon["parties"]:
            party_name = party.get("name", "")
            party_id = party.get("partyId", "")
            if party_name or party_id:
                text += f"Party: {party_name or party_id}. "
                party_count += 1
        extracted_components.append(f"parties ({party_count})")
        logger.debug(f"Extracted {party_count} parties from vCon {vcon_id}")
    
    # Extract metadata if available
    metadata_fields = []
    if "metadata" in vcon:
        # Add any important metadata fields
        if "title" in vcon["metadata"]:
            text += f"Title: {vcon['metadata']['title']}. "
            metadata_fields.append("title")
        if "description" in vcon["metadata"]:
            text += f"Description: {vcon['metadata']['description']}. "
            metadata_fields.append("description")
        if "created" in vcon["metadata"]:
            text += f"Created: {vcon['metadata']['created']}. "
            metadata_fields.append("created")
        
        if metadata_fields:
            extracted_components.append(f"metadata ({', '.join(metadata_fields)})")
            logger.debug(f"Extracted metadata fields: {', '.join(metadata_fields)} from vCon {vcon_id}")
    
    raw_text = text.strip()
    raw_text_length = len(raw_text)
    
    logger.info(f"Extracted components from vCon {vcon_id}: {', '.join(extracted_components)}")
    logger.info(f"Raw text length: {raw_text_length} characters")
    
    # Generate AI description ONLY if there's no summary or transcript AND there's enough content
    if not (has_summary or has_transcript) and len(raw_text) > 10:
        logger.info(f"No summary or transcript found for vCon {vcon_id}, generating AI description")
        try:
            logger.info(f"Generating AI description for vCon {vcon_id}")
            ai_start_time = time.time()
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an assistant that creates concise descriptions of conversation content."},
                    {"role": "user", "content": f"Generate a brief description (max 100 words) that summarizes this conversation content: {raw_text[:4000]}"}
                ],
                max_tokens=150,
                temperature=0.5
            )
            
            ai_description = response.choices[0].message.content.strip()
            ai_time_taken = time.time() - ai_start_time
            
            logger.info(f"AI description generated in {ai_time_taken:.2f}s for vCon {vcon_id}")
            final_text = f"{ai_description}\n\nRaw Content: {raw_text}"
            
            total_time = time.time() - start_time
            logger.info(f"Total processing time for vCon {vcon_id}: {total_time:.2f}s")
            return final_text
        except Exception as e:
            logger.error(f"Failed to generate AI description for vCon {vcon_id}: {str(e)}")
            st.warning(f"Could not generate AI description: {e}")
            return raw_text
    elif has_summary or has_transcript:
        logger.info(f"vCon {vcon_id} already has summary or transcript, skipping AI description generation")
    
    total_time = time.time() - start_time
    logger.info(f"Total processing time for vCon {vcon_id}: {total_time:.2f}s")
    return raw_text

with create_tab:
    st.header("Create a New Collection")
    
    collection_name = st.text_input("Collection Name", "vcons_collection")
    
    if st.button("Create Collection"):
        if utility.has_collection(collection_name):
            st.warning(f"Collection '{collection_name}' already exists.")
        else:
            # Define collection schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="vcon_uuid", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="party_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM)
            ]
            
            schema = CollectionSchema(fields=fields, description="vCons collection for semantic search")
            
            try:
                collection = Collection(name=collection_name, schema=schema)
                
                # Create an IVF_FLAT index for fast vector search
                index_params = {
                    "metric_type": "L2",
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 128}
                }
                collection.create_index(field_name="embedding", index_params=index_params)
                
                st.success(f"Collection '{collection_name}' created successfully!")
            except Exception as e:
                st.error(f"Failed to create collection: {e}")

with load_tab:
    st.header("Load vCons into Milvus")
    
    # Get available collections
    collections = utility.list_collections()
    if not collections:
        st.warning("No collections found. Please create a collection first.")
    else:
        selected_collection = st.selectbox("Select Collection", collections)
        
        if st.button("Load vCons"):
            vcons = common.get_vcons()
            
            if not vcons:
                st.warning("No vCons found in the database.")
            else:
                with st.status(f"Loading {len(vcons)} vCons into Milvus") as status:
                    collection = Collection(selected_collection)
                    collection.load()
                    
                    data = []
                    for i, vcon in enumerate(vcons):
                        # Extract text from vCon
                        text = extract_text_from_vcon(vcon)
                        
                        # Get party identifier
                        party_id = vcon.get("parties", [{}])[0].get("partyId", "") if vcon.get("parties") else ""
                        
                        # Get embedding
                        embedding = get_embedding(text)
                        
                        # Prepare data for insertion
                        data.append({
                            "vcon_uuid": vcon["uuid"],
                            "party_id": party_id,
                            "text": text,
                            "embedding": embedding
                        })
                        
                        # Update status
                        status.update(label=f"Processed {i+1}/{len(vcons)} vCons")
                        
                        # Insert in batches of 100 to avoid memory issues
                        if len(data) >= 100 or i == len(vcons) - 1:
                            collection.insert(data)
                            data = []
                    
                    collection.flush()
                    st.success(f"Successfully loaded {len(vcons)} vCons into Milvus!")

with search_tab:
    st.header("Search vCons")
    
    collections = utility.list_collections()
    if not collections:
        st.warning("No collections found. Please create a collection first.")
    else:
        selected_collection = st.selectbox("Select Collection for Search", collections)
        search_text = st.text_input("Search Query")
        top_k = st.slider("Number of Results", min_value=1, max_value=50, value=5)
        
        if st.button("Search") and search_text:
            # Get embedding for search query
            query_embedding = get_embedding(search_text)
            
            collection = Collection(selected_collection)
            collection.load()
            
            # Search parameters
            search_params = {
                "metric_type": "L2",
                "params": {"nprobe": 10}
            }
            
            results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["vcon_uuid", "party_id", "text"]
            )
            
            st.subheader("Search Results")
            
            for i, hits in enumerate(results):
                for hit in hits:
                    # Access fields from the correct location - the fields dictionary
                    fields = hit.entity.fields if hasattr(hit.entity, 'fields') else {}
                    
                    # Get data from the fields dictionary
                    vcon_uuid = fields.get('vcon_uuid', 'Unknown')
                    party_id = fields.get('party_id', 'N/A')
                    text_content = fields.get('text', '')
                    
                    with st.expander(f"Score: {hit.score:.4f}, UUID: {vcon_uuid}"):
                        st.write(f"**Party ID:** {party_id}")
                        st.write("**Text:**")
                        st.text(text_content[:1000] + "..." if len(text_content) > 1000 else text_content)
                        
                        # Keep debug info for now
                        st.write("---")
                        st.write("**Debug Info:**")
                        st.write(f"Entity type: {type(hit.entity)}")
                        if hasattr(hit.entity, 'fields'):
                            st.write(f"Fields: {hit.entity.fields}")

with delete_tab:
    st.header("Delete Collection")
    
    collections = utility.list_collections()
    if not collections:
        st.warning("No collections found.")
    else:
        collection_to_delete = st.selectbox("Select Collection to Delete", collections)
        
        if st.button("Delete Collection"):
            confirm = st.text_input("Type the collection name to confirm deletion")
            
            if confirm == collection_to_delete:
                try:
                    utility.drop_collection(collection_to_delete)
                    st.success(f"Collection '{collection_to_delete}' deleted successfully!")
                except Exception as e:
                    st.error(f"Failed to delete collection: {e}")
            else:
                st.warning("Collection name doesn't match. Deletion aborted.")

@st.cache_data(ttl="5m", show_spinner=False)
def get_collection_list():
    return utility.list_collections()

with list_tab:
    st.header("List Collections")
    
    if st.button("Refresh Collections"):
        # Use st.cache_data.clear() to force refresh when button is clicked
        st.cache_data.clear()
        collections = get_collection_list()
        
        if not collections:
            st.info("No collections found.")
        else:
            st.write(f"Found {len(collections)} collections:")
            
            for collection_name in collections:
                with st.expander(collection_name):
                    try:
                        collection = Collection(collection_name)
                        stats = collection.stats()
                        
                        st.write(f"**Row Count:** {stats['row_count']}")
                        st.write(f"**Created At:** {datetime.fromtimestamp(collection.describe().created_utc_timestamp/1000)}")
                        
                        # Show index information
                        index_info = collection.index().describe()
                        st.write("**Index Information:**")
                        st.json(index_info)
                    except Exception as e:
                        st.error(f"Failed to get statistics: {e}")

# Close Milvus connection when app is done
connections.disconnect("default") 