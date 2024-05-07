import streamlit as st
import pymongo
import json
import lib.common as common
import pandas as pd

common.init_session_state()

# This page is for general information about the system, the number of vCons, etc.
# It's also a place for quality metrics like "Number of vCons analyzed" and "Number of vCons with summaries"
st.title("VCON INFO")

# Function to initialize the MongoDB connection
def get_mongo_client():
    url = st.secrets["mongo_db"]["url"]
    return pymongo.MongoClient(url)


client = get_mongo_client()
db = client[st.secrets["mongo_db"]["db"]]
collection = db[st.secrets["mongo_db"]["collection"]]
vcon_count = collection.count_documents({})

# Display the number of vCons in the database
st.metric("TOTAL VCON COUNT", vcon_count)

# Display the number of vCons with summaries
pipeline = [
    {
        "$match": {
            "analysis.type": "summary"
        }
    },
    {
        "$count": "count"
    }
]
results = list(collection.aggregate(pipeline))
vcon_with_summaries = results[0]["count"] if results else 0
st.metric("VCON COUNT WITH SUMMARIES", vcon_with_summaries)

# Display a chart of the number of vCons per day for the past 30 days
st.write("## VCON COUNT BY DAY")
pipeline = [
    {
        "$match": {
            "created_at": {
                "$exists": True
            }
        }
    },
     {
        "$addFields": {
            "date_created_at": {
                "$toDate": "$created_at"
            }
        }
    },
    {
        "$group": {
            "_id": {
                "$dateToString": {
                    "format": "%Y-%m-%d",
                    "date": "$date_created_at"
                }
            },
            "count": {"$sum": 1}
        }
    },
    {
        "$sort": {
            "_id": 1
        }
    }
]
results = list(collection.aggregate(pipeline))
dates = [r["_id"] for r in results]
counts = [r["count"] for r in results]

# Create a DataFrame with your data
data = pd.DataFrame({
  'Dates': dates,
  'Counts': counts
})

# Set Dates as the index
data = data.set_index('Dates')

# Display a line chart
st.line_chart(data)

# Display a chart of the number of vCons per day the last day
st.write("## VCON COUNT BY HOUR")
pipeline = [
    {
        "$match": {
            "created_at": {
                "$gt": pd.Timestamp.now() - pd.Timedelta("1 day")
            }
        }
    },
    {
        "$group": {
            "_id": {
                "$dateToString": {
                    "format": "%Y-%m-%d %H",
                    "date": "$created_at"
                }
            },
            "count": {"$sum": 1}
        }
    },
    {
        "$sort": {
            "_id": 1
        }
    }
]
results = list(collection.aggregate(pipeline))
dates = [r["_id"] for r in results]
counts = [r["count"] for r in results]

# Create a DataFrame with your data
data = pd.DataFrame({
  'Dates': dates,
  'Counts': counts
})

# Set Dates as the index
data = data.set_index('Dates')
# Display a line chart
st.line_chart(data)

