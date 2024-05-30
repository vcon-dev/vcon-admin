# vCon Admin

## Summary

This streamlit application is an adminstrative toolkit for conserver
developers, testers and operators.  With it, you can: 
- Import and export of vCons from various storages,including REDIS (the native conserver datastore), S3, JSONL, JSON and mongodb.
- View the status and configuration of the local system and docker containers, 
including real-time docker logs
- Upload vCons into an elasticsearch server for QA testing
- Upload vCons into an OpenAI vector store for QA testing
- Run a ChatGPT prompt on a subset of local vCons

It is written in Streamlit, uses Mongo as master data store, and uses Docker 
for containerization, and is packaged with elasticsearch and mongo. 

## Quick Install

_Tested on clean  4 GB Memory / 2 Intel vCPUs / 120 GB Disk / NYC3 - Ubuntu 24.04 (LTS) x64_

  0) _(Optional but recommended for external servers)_ ufw allow 8501 && ufw allow ssh && ufw enable
  1) _(Only if docker is not installed)_ snap install docker
  2) git clone https://github.com/vcon-dev/vcon-admin.git
  3) cd vcon-admin
  4) mkdir .streamlit
  5) vim .streamlit/secrets.toml
  6) docker network create conserver
  7) docker compose up -d
  8) Visit http://localhost:8501

## Sample secrets.toml

Copy and insert this secrets.toml file in the .streamlit/ directory. 

- AWS keys are required for S3 access for import/export
- MongoDB is the local database that vcon_admin uses
- OpenAI is used on the workbench and the ChatGPT section

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

## Special Functionality

### ChatGPT
This page interacts with OpenAI's API and provides a user interface for managing files and interacting with an AI assistant. Here's a summary of its main functionalities:


1. It connects to OpenAI using the provided API key and initializes a new conversation thread if one doesn't exist.

2. In the "Upload Files" tab, it allows the user to upload files to OpenAI. The user can choose the purpose of the files and the vector store to which the files will be uploaded.

3. In the "Download Files" tab, it allows the user to download files from OpenAI to their local machine.

4. In the "Delete Files" tab, it allows the user to delete all the files in the selected purpose from OpenAI.

5. In the "List Files" tab, it allows the user to list all of the files currently uploaded to OpenAI.

6. It provides a section for Assistant Testing, where the user can select an assistant and view its details.

7. It provides a chat interface for the user to interact with the selected assistant. The user can input a message, which is then sent to the assistant for processing. The assistant's response is displayed in the chat interface.

### Workbench
The Streamlit app titled "VCON WORKBENCH" is designed for analyzing vCon (voice conversation) data using OpenAI's API and MongoDB. Here's a summary of its functionality:


- **ADD VCONS Tab:**
   - Allows users to add vCon UUIDs manually or find a random vCon from the database.
   - Displays vCon details, including UUID, creation and update timestamps, and summary.
   - Users can add vCons to the input list, view details, or delete them from the workbench.

- **CONFIGURE PROMPTS Tab:**
   - Enables users to create prompts for OpenAI by specifying system prompt, user prompt, model name, temperature, and input type (complete, summary, or transcript).
   - The prompts are stored in the session state.

- **RUN ANALYSIS Tab:**
   - Users can run the analysis for the vCons listed in the session state.
   - The tab shows the configured prompt and allows users to run the analysis.
   - For each vCon, it fetches the appropriate content based on the input type and calls OpenAI's API to generate a response.
   - The generated response is displayed along with a link to the vCon details.



### Inspector
  - View details of a specific vCon by entering its UUID
  - Display summary, analysis, dialog, parties, and attachments of the selected vCon
  - Download the vCon as a JSON file
  - Add the vCon to the workbench for analysis



## Setup

1. Install the required dependencies:
  - streamlit
  - pymongo
  - openai
  - redis
  - boto3

2. Set up the necessary secrets in Streamlit's secrets management:
  - `mongo_db`: URL, database name, and collection name for the MongoDB connection
  - `aws`: AWS access key ID, secret access key, and default region for S3 access

3. Run the Streamlit application:

## Usage

1. Navigate to the desired page using the sidebar menu.
2. Follow the instructions on each page to import, export, inspect, or analyze vCons.
3. Use the admin portal to view and modify the system configuration.

## File Structure

- `workbench.py`: Main page for managing and analyzing vCons
- `inspect.py`: Page for inspecting individual vCons
- `import.py`: Page for importing vCons from various sources
- `export.py`: Page for exporting vCons to different formats and destinations
- `admin.py`: Admin portal for system configuration
- `custom_info.md`: Custom information displayed in the admin portal

## Dependencies

- Streamlit: Web framework for building interactive data applications
- PyMongo: MongoDB driver for Python
- OpenAI: Library for accessing OpenAI's language models
- Redis: Python client for Redis database
- Boto3: AWS SDK for Python

Note: Make sure to properly set up the required secrets and environment variables before running the application.
