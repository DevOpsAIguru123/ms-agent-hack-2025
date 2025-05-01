from langchain_google_community import GoogleSearchAPIWrapper
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access API keys from environment variables
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["GOOGLE_CSE_ID"] = os.getenv("GOOGLE_CSE_ID")

google_search = GoogleSearchAPIWrapper()

def perform_google_search(query):
    results = google_search.run(query)
    return results

# Usage:
print(perform_google_search("Microsoft AI hackathon 2025"))
