import streamlit as st
import lib.common as common
import json
import os
import logging
import time
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from openai import OpenAI
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

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

# Initialize active tab tracking in session state
if 'active_tab_index' not in st.session_state:
    st.session_state.active_tab_index = 0

# Initialize save operation status in session state
if 'save_status' not in st.session_state:
    st.session_state.save_status = None
    st.session_state.save_error = None
    st.session_state.save_message = None

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

# Function to ensure Milvus connection is established
def ensure_milvus_connection():
    try:
        # Check if connection exists by attempting a simple operation
        utility.list_collections()
    except Exception as e:
        st.write(f"Reconnecting to Milvus: {e}")
        try:
            # Attempt to disconnect first in case there's a stale connection
            try:
                connections.disconnect("default")
            except:
                pass
            # Connect to Milvus
            connections.connect(host=milvus_host, port=milvus_port)
            return True
        except Exception as e:
            st.error(f"Failed to connect to Milvus: {e}")
            return False
    return True

# Connect to Milvus
try:
    connections.connect(host=milvus_host, port=milvus_port)
    st.success(f"Connected to Milvus at {milvus_host}:{milvus_port}")
except Exception as e:
    st.error(f"Failed to connect to Milvus: {e}")

# Create tabs for different operations
tabs = ["Create Collection", "Load vCons", "Search", "Delete Collection", "List Collections", "Debug Embedding"]
create_tab, load_tab, search_tab, delete_tab, list_tab, debug_tab = st.tabs(tabs)

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

# Function to extract party ID from vCon with better handling
def extract_party_id(vcon):
    """Extract a meaningful party identifier from a vCon based on standard vCon structure"""
    logger.debug(f"Extracting party ID from vCon {vcon.get('uuid', 'unknown')}")
    
    if not vcon.get("parties"):
        logger.debug("No parties array found in vCon")
        # Try alternative fields if parties is not available
        if vcon.get("metadata", {}).get("creator"):
            return vcon["metadata"]["creator"]
        return "no_party_info"
    
    # Try to find a non-empty party ID from any party in the array
    for party in vcon["parties"]:
        # First priority: UUID as it's unique
        if party.get("uuid"):
            logger.debug(f"Using party UUID: {party['uuid']}")
            return party["uuid"]
        
        # Second priority: Contact methods (tel, mailto)
        if party.get("tel"):
            logger.debug(f"Using party telephone: {party['tel']}")
            return f"tel:{party['tel']}"
        
        if party.get("mailto"):
            logger.debug(f"Using party email: {party['mailto']}")
            return f"mailto:{party['mailto']}"
        
        # Third priority: Name and role combined
        if party.get("name") and party.get("role"):
            combined = f"{party['role']}:{party['name']}"
            logger.debug(f"Using party role+name: {combined}")
            return combined
        
        # Fourth priority: Just name or role
        if party.get("name"):
            logger.debug(f"Using party name: {party['name']}")
            return party["name"]
        
        if party.get("role"):
            logger.debug(f"Using party role: {party['role']}")
            return party["role"]
        
        # Fifth priority: Any other unique identifier in the party object
        for field in ["partyId", "PartyId", "party_id", "id", "userID", "userId"]:
            if party.get(field):
                logger.debug(f"Found non-standard ID {party[field]} using field {field}")
                return party[field]
    
    # If we got here but have parties, use the first party's index as identifier
    if vcon["parties"]:
        logger.debug("No explicit identifiers found, using party index")
        return f"party_index:0"
    
    logger.debug("No usable party identifier found")
    return "unknown_party"

# Function to handle the Milvus save operation outside the main app flow
def save_to_milvus(collection_name, vcon, party_id, text, embedding):
    try:
        vcon_uuid = vcon["uuid"]  # Extract UUID from the vCon object
        logger.info(f"Starting save operation for vCon {vcon_uuid} to collection {collection_name}")
        
        # Ensure Milvus connection
        connection_status = ensure_milvus_connection()
        if not connection_status:
            st.session_state.save_status = "error"
            st.session_state.save_error = "Failed to establish Milvus connection"
            logger.error("Milvus connection failed during save_to_milvus function")
            return False
        
        # Validate collection exists
        if not utility.has_collection(collection_name):
            st.session_state.save_status = "error"
            st.session_state.save_error = f"Collection {collection_name} no longer exists"
            logger.error(f"Collection {collection_name} does not exist in save_to_milvus function")
            return False
        
        # Load collection
        collection = Collection(collection_name)
        collection.load()
        
        # Validate embedding
        if not isinstance(embedding, list) or len(embedding) != EMBEDDING_DIM:
            error_msg = f"Invalid embedding format: expected list with {EMBEDDING_DIM} dimensions"
            st.session_state.save_status = "error"
            st.session_state.save_error = error_msg
            logger.error(error_msg)
            return False
        
        # Extract key metadata from the vCon object and ensure they are strings
        metadata = vcon.get("metadata", {})
        created_at = str(metadata.get("created_at", "")) if metadata.get("created_at") is not None else ""
        updated_at = str(metadata.get("updated_at", "")) if metadata.get("updated_at") is not None else ""
        subject = str(vcon.get("subject", "")) if vcon.get("subject") is not None else ""
        title = str(metadata.get("title", "")) if metadata.get("title") is not None else ""
        
        # Content indicators
        has_transcript = bool(vcon.get("transcript"))
        has_summary = bool(vcon.get("summary"))
        party_count = len(vcon.get("parties", []))
        
        # Ensure party_id is a string
        party_id = str(party_id) if party_id is not None else ""
        
        # Ensure text is a string 
        text = str(text) if text is not None else ""
        
        # Prepare and insert data
        data = [{
            "vcon_uuid": vcon_uuid,
            "party_id": party_id,
            "text": text,
            "embedding": embedding,
            "created_at": created_at,
            "updated_at": updated_at,
            "subject": subject,
            "metadata_title": title,
            "has_transcript": has_transcript,
            "has_summary": has_summary,
            "party_count": party_count,
            "embedding_model": "text-embedding-3-small",
            "embedding_version": "1.0"
        }]
        
        # Log the data types being inserted
        logger.debug(f"Data types for insertion: vcon_uuid: {type(vcon_uuid)}, subject: {type(subject)}, text: {type(text)} (length: {len(text)})")
        
        # Insert and flush
        insert_result = collection.insert(data)
        logger.info(f"Insert result: {insert_result}")
        
        flush_result = collection.flush()
        logger.info(f"Flush result: {flush_result}")
        
        st.session_state.save_status = "success"
        st.session_state.save_message = f"Successfully saved vCon {vcon_uuid} to Milvus!"
        logger.info(f"Successfully saved vCon {vcon_uuid} to collection {collection_name}")
        return True
        
    except Exception as e:
        logger.exception(f"Exception in save_to_milvus function: {str(e)}")
        st.session_state.save_status = "error"
        st.session_state.save_error = str(e)
        return False

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
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
                FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=30),
                FieldSchema(name="updated_at", dtype=DataType.VARCHAR, max_length=30),
                FieldSchema(name="subject", dtype=DataType.VARCHAR, max_length=255),
                FieldSchema(name="metadata_title", dtype=DataType.VARCHAR, max_length=255),
                FieldSchema(name="has_transcript", dtype=DataType.BOOL),
                FieldSchema(name="has_summary", dtype=DataType.BOOL),
                FieldSchema(name="party_count", dtype=DataType.INT16),
                FieldSchema(name="embedding_model", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="embedding_version", dtype=DataType.VARCHAR, max_length=20),
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
    
    # Ensure Milvus connection is active
    ensure_milvus_connection()
    
    # Get available collections
    collections = utility.list_collections()
    if not collections:
        st.warning("No collections found. Please create a collection first.")
    else:
        selected_collection = st.selectbox("Select Collection", collections, key="load_collection_select")
        
        # Add loading mode selection
        loading_mode = st.radio(
            "Loading Mode", 
            ["Load All vCons", "Load Only Missing vCons"],
            help="Choose to load all vCons or only add those missing in Milvus"
        )
        
        # Add limit parameter
        limit_col1, limit_col2 = st.columns([3, 1])
        with limit_col1:
            st.write("Limit the number of vCons to process (0 = no limit)")
        with limit_col2:
            vcon_limit = st.number_input("Max vCons", min_value=0, value=0, step=10, help="Set a limit on how many vCons to process. Use 0 for no limit.")
        
        # Function to handle batch loading
        def load_vcons_to_milvus():
            vcons = common.get_vcons()
            
            if not vcons:
                st.warning("No vCons found in the database.")
                return
            
            # Apply limit if specified
            if vcon_limit > 0 and len(vcons) > vcon_limit:
                logger.info(f"Limiting vCon processing to {vcon_limit} out of {len(vcons)} total vCons")
                st.info(f"Processing {vcon_limit} out of {len(vcons)} available vCons (limit applied)")
                vcons = vcons[:vcon_limit]
                
            # Ensure connection is active right before querying
            connection_status = ensure_milvus_connection()
            if not connection_status:
                st.error("Failed to establish Milvus connection. Cannot proceed with loading operation.")
                logger.error("Milvus connection failed during load operation")
                return
                
            # Verify collection still exists
            if not utility.has_collection(selected_collection):
                st.error(f"Collection {selected_collection} no longer exists or is not accessible")
                logger.error(f"Collection {selected_collection} does not exist at load time")
                return
                
            # Get existing vCon UUIDs from Milvus if in "missing only" mode
            existing_uuids = set()
            if loading_mode == "Load Only Missing vCons":
                try:
                    logger.info(f"Loading collection {selected_collection} to check existing vCons")
                    collection = Collection(selected_collection)
                    collection.load()
                    
                    # Query to get all existing UUIDs
                    logger.info("Querying for existing vCon UUIDs")
                    results = collection.query(
                        expr="vcon_uuid != ''",
                        output_fields=["vcon_uuid"]
                    )
                    existing_uuids = {r['vcon_uuid'] for r in results}
                    logger.info(f"Found {len(existing_uuids)} existing vCons in Milvus")
                    st.info(f"Found {len(existing_uuids)} existing vCons in Milvus")
                except Exception as e:
                    logger.exception(f"Error querying existing vCons: {str(e)}")
                    st.error(f"Error querying existing vCons: {str(e)}")
                    with st.expander("Exception Details", expanded=True):
                        st.exception(e)
                    return
            
            # Filter vCons if in "missing only" mode
            if loading_mode == "Load Only Missing vCons":
                to_process = [vcon for vcon in vcons if vcon["uuid"] not in existing_uuids]
                logger.info(f"Found {len(to_process)} vCons to add to Milvus")
                st.info(f"Found {len(to_process)} vCons to add to Milvus")
            else:
                to_process = vcons
            
            if not to_process:
                st.success("No new vCons to add. All vCons already exist in Milvus!")
                return
                
            # Create a fresh collection reference for insertion
            try:
                collection = Collection(selected_collection)
                collection.load()
            except Exception as e:
                logger.exception(f"Error loading collection for insertion: {str(e)}")
                st.error(f"Error loading collection for insertion: {str(e)}")
                with st.expander("Exception Details", expanded=True):
                    st.exception(e)
                return
                
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Process in batches
            batch_size = 100
            total_success = 0
            total_failed = 0
            
            for batch_start in range(0, len(to_process), batch_size):
                batch_end = min(batch_start + batch_size, len(to_process))
                batch = to_process[batch_start:batch_end]
                
                status_text.text(f"Processing batch {batch_start//batch_size + 1}/{(len(to_process)-1)//batch_size + 1} ({batch_start+1}-{batch_end}/{len(to_process)})")
                
                # Prepare batch data
                data = []
                batch_failed = 0
                
                for i, vcon in enumerate(batch):
                    try:
                        # Extract text from vCon
                        text = extract_text_from_vcon(vcon)
                        
                        # Get party identifier with better extraction
                        party_id = extract_party_id(vcon)
                        
                        # Get embedding
                        embedding = get_embedding(text)
                        
                        # Validate embedding
                        if not isinstance(embedding, list) or len(embedding) != EMBEDDING_DIM:
                            error_msg = f"Invalid embedding for vCon {vcon['uuid']}: expected list with {EMBEDDING_DIM} dimensions"
                            logger.error(error_msg)
                            batch_failed += 1
                            continue
                        
                        # Extract key metadata and ensure they are strings
                        metadata = vcon.get("metadata", {})
                        created_at = str(metadata.get("created_at", "")) if metadata.get("created_at") is not None else ""
                        updated_at = str(metadata.get("updated_at", "")) if metadata.get("updated_at") is not None else ""
                        subject = str(vcon.get("subject", "")) if vcon.get("subject") is not None else ""
                        title = str(metadata.get("title", "")) if metadata.get("title") is not None else ""
                        
                        # Content indicators
                        has_transcript = bool(vcon.get("transcript"))
                        has_summary = bool(vcon.get("summary"))
                        party_count = len(vcon.get("parties", []))
                        
                        # Ensure party_id is a string
                        party_id = str(party_id) if party_id is not None else ""
                        
                        # Ensure text is a string
                        text = str(text) if text is not None else ""
                        
                        # Prepare enriched data object
                        data.append({
                            "vcon_uuid": vcon["uuid"],
                            "party_id": party_id,
                            "text": text,
                            "embedding": embedding,
                            "created_at": created_at,
                            "updated_at": updated_at,
                            "subject": subject,
                            "metadata_title": title,
                            "has_transcript": has_transcript,
                            "has_summary": has_summary,
                            "party_count": party_count,
                            "embedding_model": "text-embedding-3-small",
                            "embedding_version": "1.0"
                        })
                        
                    except Exception as e:
                        logger.exception(f"Error processing vCon {vcon.get('uuid', 'unknown')}: {str(e)}")
                        batch_failed += 1
                
                # Insert batch if we have data
                if data:
                    try:
                        logger.info(f"Inserting batch of {len(data)} vCons")
                        insert_result = collection.insert(data)
                        logger.info(f"Insert result: {insert_result}")
                        collection.flush()
                        total_success += len(data)
                    except Exception as e:
                        logger.exception(f"Error inserting batch: {str(e)}")
                        st.error(f"Error inserting batch: {str(e)}")
                        with st.expander(f"Batch {batch_start//batch_size + 1} Error Details", expanded=False):
                            st.exception(e)
                        total_failed += len(data)
                
                total_failed += batch_failed
                
                # Update progress
                progress = (batch_end) / len(to_process)
                progress_bar.progress(progress)
            
            # Final update
            if total_failed > 0:
                st.warning(f"Completed with {total_success} vCons loaded successfully and {total_failed} failures.")
                logger.warning(f"Completed with {total_success} vCons loaded successfully and {total_failed} failures.")
            else:
                st.success(f"Successfully loaded {total_success} vCons into Milvus!")
                logger.info(f"Successfully loaded {total_success} vCons into Milvus!")
        
        if st.button("Load vCons", key="load_vcons_button"):
            with st.spinner("Processing vCons..."):
                load_vcons_to_milvus()

with search_tab:
    st.header("Search vCons")
    
    collections = utility.list_collections()
    if not collections:
        st.warning("No collections found. Please create a collection first.")
    else:
        selected_collection = st.selectbox("Select Collection for Search", collections, key="search_collection_select")
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
                    # Access the entity data correctly - Milvus returns entity as a dict-like object
                    # Try multiple access patterns to handle different Milvus SDK versions
                    if hasattr(hit, 'entity') and isinstance(hit.entity, dict):
                        # Direct dictionary access for newer SDK versions
                        vcon_uuid = hit.entity.get('vcon_uuid', 'Unknown')
                        party_id = hit.entity.get('party_id', 'N/A')
                        text_content = hit.entity.get('text', '')
                    elif hasattr(hit, 'entity') and hasattr(hit.entity, 'fields'):
                        # Access through fields attribute for some SDK versions
                        fields = hit.entity.fields
                        vcon_uuid = fields.get('vcon_uuid', 'Unknown')
                        party_id = fields.get('party_id', 'N/A')
                        text_content = fields.get('text', '')
                    else:
                        # Fallback for other SDK versions
                        vcon_uuid = getattr(hit, 'vcon_uuid', 'Unknown')
                        party_id = getattr(hit, 'party_id', 'N/A')
                        text_content = getattr(hit, 'text', '')
                    
                    with st.expander(f"Score: {hit.score:.4f}, UUID: {vcon_uuid}"):
                        st.write(f"**Party ID:** {party_id}")
                        st.write("**Text:**")
                        st.text(text_content[:1000] + "..." if len(text_content) > 1000 else text_content)
                        
                        # Add a link to view the full vCon
                        if vcon_uuid != 'Unknown':
                            st.markdown(f"[View full vCon](/vcon_viewer?uuid={vcon_uuid})")
                        
                        # Keep debug info but make it less prominent
                        st.write(f"Entity type: {type(hit.entity)}")
                        st.write(f"Entity content: {hit.entity}")
                        st.write(f"Hit attributes: {dir(hit)}")
                        st.write(f"Hit type: {type(hit)}")
                        st.write(f"Query embedding: {query_embedding}")

with delete_tab:
    st.header("Delete Collection")
    
    collections = utility.list_collections()
    if not collections:
        st.warning("No collections found.")
    else:
        collection_to_delete = st.selectbox("Select Collection to Delete", collections, key="delete_collection_select")
        
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
# connections.disconnect("default")

# Add Debug Embedding tab functionality
with debug_tab:
    # Track that we're in the debug tab
    st.session_state.active_tab_index = 5
    
    st.header("Debug Embedding Generation")
    st.write("Test embedding generation for a single vCon and optionally save it to a Milvus collection.")
    
    # Display save operation status if it exists
    if st.session_state.save_status == "success":
        st.success(st.session_state.save_message)
        # Clear the status after displaying
        st.session_state.save_status = None
    elif st.session_state.save_status == "error":
        st.error(f"Error saving to Milvus: {st.session_state.save_error}")
        # Show detailed error in an expander
        with st.expander("Error Details", expanded=True):
            st.write(st.session_state.save_error)
        # Clear the status after displaying
        st.session_state.save_status = None
    
    # Get all vCons for selection
    vcons = common.get_vcons()
    
    if not vcons:
        st.warning("No vCons found in the database. Please add vCons first.")
    else:
        # Store embedding in session state to persist across reruns
        if 'current_embedding' not in st.session_state:
            st.session_state.current_embedding = None
            st.session_state.current_raw_text = None
            st.session_state.current_vcon = None
        
        # Create a dropdown to select a vCon by UUID + metadata
        vcon_options = {f"{v.get('uuid', 'unknown')} - {v.get('metadata', {}).get('title', 'No Title')}": v 
                        for v in vcons}
        
        selected_vcon_key = st.selectbox(
            "Select a vCon to embed", 
            options=list(vcon_options.keys()),
            help="Choose a vCon from the dropdown to generate and view its embedding",
            key="debug_vcon_select"
        )
        
        selected_vcon = vcon_options[selected_vcon_key] if selected_vcon_key else None
        
        if selected_vcon:
            # Display the original vCon before embedding
            with st.expander("View Original vCon JSON", expanded=False):
                st.json(selected_vcon)
        
        # Function to generate embedding and store in session state
        def generate_embedding():
            st.session_state.current_vcon = selected_vcon
            st.session_state.current_raw_text = extract_text_from_vcon(selected_vcon)
            st.session_state.current_embedding = get_embedding(st.session_state.current_raw_text)
            logger.info(f"Generated embedding for vCon {selected_vcon['uuid']} with dimensions {len(st.session_state.current_embedding)}")
        
        # Generate embedding on button click
        if selected_vcon and st.button("Generate Embedding", key="debug_generate_button", on_click=generate_embedding if selected_vcon else None):
            # The actual work happens in the on_click callback
            pass
        
        # If we have an embedding in session state, display it
        if st.session_state.current_embedding is not None and st.session_state.current_vcon is not None:
            # Extract and display the raw text
            raw_text = st.session_state.current_raw_text
            
            st.subheader("Extracted Text")
            st.text_area("Text used for embedding", raw_text, height=200, key="debug_extracted_text")
            
            # Get embedding from session state
            embedding = st.session_state.current_embedding
            
            st.subheader("Generated Embedding")
            
            # Display embedding stats
            st.write(f"Embedding dimensions: {len(embedding)}")
            st.write(f"Embedding type: {type(embedding)}")
            
            # Calculate and display basic stats about the embedding vector
            embedding_array = np.array(embedding)
            
            stats_col1, stats_col2, stats_col3 = st.columns(3)
            with stats_col1:
                st.metric("Min value", f"{embedding_array.min():.6f}")
            with stats_col2:
                st.metric("Max value", f"{embedding_array.max():.6f}")
            with stats_col3:
                st.metric("Mean value", f"{embedding_array.mean():.6f}")
            
            # Visualize the embedding distribution with a histogram
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.hist(embedding_array, bins=50)
            ax.set_title("Embedding Value Distribution")
            ax.set_xlabel("Value")
            ax.set_ylabel("Frequency")
            st.pyplot(fig)
            
            # Show first few values of the embedding vector
            with st.expander("View embedding vector (first 20 values)"):
                st.write(embedding[:20])
            
            # Optionally save to a collection
            st.subheader("Save to Milvus")
            
            # Ensure Milvus connection is active before listing collections
            ensure_milvus_connection()
            collections = utility.list_collections()
            
            # Log available collections
            logger.info(f"Available collections for saving: {collections}")
            
            if collections:
                # Create UI for saving to Milvus
                save_col1, save_col2 = st.columns([3, 1])
                
                with save_col1:
                    save_collection = st.selectbox(
                        "Select Collection", 
                        collections, 
                        key="debug_save_collection_select"
                    )
                
                # Function to handle save button click
                def save_button_callback():
                    logger.info(f"Save button clicked for vCon {st.session_state.current_vcon['uuid']}")
                    
                    # Get party identifier with better extraction
                    party_id = extract_party_id(st.session_state.current_vcon)
                    
                    # Execute save operation via the helper function - passing the full vCon object
                    save_to_milvus(
                        save_collection,
                        st.session_state.current_vcon,  # Pass the complete vCon object
                        party_id,
                        st.session_state.current_raw_text,
                        st.session_state.current_embedding
                    )
                
                with save_col2:
                    st.button(
                        "Save to Milvus", 
                        key="debug_save_button", 
                        on_click=save_button_callback,
                        disabled=st.session_state.current_embedding is None
                    )
            else:
                st.warning("No collections found. Create a collection first to save this embedding.")
                logger.warning("Attempted to save embedding but no collections exist")
            
            st.success("Embedding generation completed!") 