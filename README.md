# VCON Workbench

This is a multi-page Streamlit application for managing and analyzing vCons (virtual conversations). It provides functionality to import, export, inspect, and run analysis on vCons stored in a MongoDB database.

## Pages

1. **Workbench (workbench.py)**
  - Add vCons to the workbench by ID or find random vCons from the database
  - Configure prompts for analysis using OpenAI's chat completion API
  - Run analysis on the selected vCons and display the results

2. **Inspector (inspect.py)**
  - View details of a specific vCon by entering its UUID
  - Display summary, analysis, dialog, parties, and attachments of the selected vCon
  - Download the vCon as a JSON file
  - Add the vCon to the workbench for analysis

3. **Import (import.py)**
  - Upload a single vCon file or bulk import vCons from a JSONL file
  - Import vCons from a URL or pasted JSON text
  - Import vCons from a Redis database or an Amazon S3 bucket

4. **Export (export.py)**
  - Export vCons from the MongoDB database to a JSONL file or individual JSON files
  - Export vCons to a Redis database

5. **Admin (admin.py)**
  - View the current configuration of the system
  - Make changes to the configuration (functionality not implemented in the provided code)

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
