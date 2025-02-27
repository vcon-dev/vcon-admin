# vCon Admin

## Summary

This streamlit application is an administrative toolkit for conserver
developers, testers and operators. With it, you can: 
- Import and export vCons from various storages, including REDIS (the native conserver datastore), S3, JSONL, JSON, and MongoDB
- View the status and configuration of the local system and docker containers, including real-time docker logs
- Upload vCons into an Elasticsearch server for QA testing
- Upload vCons into vector databases (OpenAI and Milvus) for QA testing and semantic search
- Run a ChatGPT prompt on a subset of local vCons
- Perform analysis and visualization of vCon data

The application is built with Streamlit, uses MongoDB as the master data store, and is containerized with Docker. It includes integrations with Elasticsearch, Milvus, and OpenAI services.

## Quick Install

_Tested on clean 4 GB Memory / 2 Intel vCPUs / 120 GB Disk / Ubuntu 24.04 (LTS) x64_

  0) _(Optional but recommended for external servers)_ ufw allow 8501 && ufw allow ssh && ufw enable
  1) _(Only if docker is not installed)_ snap install docker
  2) git clone https://github.com/vcon-dev/vcon-admin.git
  3) cd vcon-admin
  4) mkdir .streamlit
  5) vim .streamlit/secrets.toml
  6) docker network create conserver
  7) docker compose up -d
  8) docker exec -it elasticsearch /usr/share/elasticsearch/bin/elasticsearch-reset-password -u elastic
  9) _(Update secrets.toml with new elastic search password)_ vim .streamlit/secrets.toml
  10) Visit http://localhost:8501

## Sample secrets.toml

Copy and insert this secrets.toml file in the .streamlit/ directory. 

- AWS keys are required for S3 access for import/export
- MongoDB is the local database that vcon_admin uses
- OpenAI is used for the workbench, vector store embeddings, and the ChatGPT section
- Elasticsearch is used for vector search and indexing
- Milvus configuration is needed for the Milvus vector database integration

```
# .streamlit/secrets.toml

[aws]
AWS_DEFAULT_REGION = "us-east-1"
AWS_ACCESS_KEY_ID="AKIA---------"
AWS_SECRET_ACCESS_KEY="XluP-----"

[mongo_db]
url = "mongodb://mongo:27017/"
db = "vcons"
collection = "vcons"

[openai]
testing_key = "sk-proj------------------------------"
api_key = "sk-proj----------------------------------"
organization = "org-------------------------------"
project = "proj_----------------------------"
vector_store_name = "vcons"
assistant_id = "asst_----------------------"

[elasticsearch]
url = "https://elasticsearch:9200"
username = "elastic"
password = "changeme"
 
[conserver]
api_url = "http://conserver:8000"
auth_token = "123456780"
```

## Milvus Integration (Optional)

For vector search capabilities with Milvus, you can use the provided docker-compose-milvus.yml file:

```bash
docker compose -f docker-compose-milvus.yml up -d
```

The Milvus integration allows you to:
- Store vCon embeddings in Milvus collections
- Perform semantic similarity searches across your vCon library
- Visualize embedding data with dimension reduction techniques
- Manage multiple Milvus collections

## Special Functionality

### vCon Inspector
- View details of a specific vCon by entering its UUID
- Display summary, analysis, dialog, parties, and attachments of the selected vCon
- Download the vCon as a JSON file
- Add the vCon to the workbench for analysis

### vCon Workbench
The Workbench allows you to analyze vCon data using OpenAI's API and MongoDB:

- **ADD VCONS Tab:**
   - Add vCon UUIDs manually or find a random vCon from the database
   - Display vCon details, including UUID, creation and update timestamps, and summary
   - Add vCons to the input list, view details, or delete them from the workbench

- **CONFIGURE PROMPTS Tab:**
   - Create prompts for OpenAI by specifying system prompt, user prompt, model name, temperature, and input type
   - Configure prompts to use complete vCon, summary, or transcript

- **RUN ANALYSIS Tab:**
   - Execute analysis on listed vCons using the configured prompts
   - View generated responses with links to vCon details

### ChatGPT Integration
This functionality connects with OpenAI's API for AI assistant interactions:

- **Upload Files:** Upload vCons to OpenAI with configurable purpose and vector store destination
- **Download Files:** Download files from OpenAI to your local machine
- **Delete Files:** Remove files from OpenAI by purpose
- **List Files:** View all files currently uploaded to OpenAI
- **Assistant Testing:** Select an assistant and view its details
- **Chat Interface:** Interact with the selected assistant through a chat interface

### Milvus Vector Database
The Milvus integration provides advanced vector search capabilities:

- Upload vCons to Milvus collections
- Generate and store embeddings using OpenAI's embedding models
- Perform semantic similarity searches
- Visualize embeddings using dimension reduction techniques
- Manage collections with creation, deletion, and inspection tools

### Import/Export
- Import vCons from REDIS, S3, JSONL, JSON, and MongoDB
- Export vCons to various formats and destinations
- Batch operations for efficient data management

## Setup

1. Install dependencies using Poetry:
```bash
poetry install
```

2. Set up the necessary secrets in Streamlit's secrets management (see Sample secrets.toml section)

3. Run the application with:
```bash
poetry run streamlit run admin.py
```

Or use Docker:
```bash
docker compose up -d
```

## Dependencies

The application uses the following main dependencies:
- Streamlit: Web framework for building interactive data applications
- PyMongo: MongoDB driver for Python
- OpenAI: Library for accessing OpenAI's language models
- Redis: Python client for Redis database
- Boto3: AWS SDK for Python
- Elasticsearch: Python client for Elasticsearch
- PyMilvus: Python client for Milvus vector database
- Docker: For container management and monitoring
- Various visualization libraries (Matplotlib, etc.)

## Development

For development, you can use the development compose file:
```bash
docker compose -f docker-compose-dev.yml up -d
```
