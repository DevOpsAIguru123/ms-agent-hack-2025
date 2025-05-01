import fitz  # PyMuPDF
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchProfile,
    VectorSearchAlgorithmConfiguration,
    HnswAlgorithmConfiguration
)
from langchain_openai import AzureOpenAIEmbeddings
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Azure Cognitive Search settings
azure_search_service_name = os.getenv("AZURE_SEARCH_ENDPOINT")
azure_search_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
azure_search_key = os.getenv("AZURE_SEARCH_API_KEY")
api_version = os.getenv("AZURE_SEARCH_API_VERSION")

# Azure OpenAI settings
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_openai_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL")

# Create clients
index_client = SearchIndexClient(
    endpoint=f"https://{azure_search_service_name}.search.windows.net",
    credential=AzureKeyCredential(azure_search_key),
    api_version=api_version
)

search_client = SearchClient(
    endpoint=f"https://{azure_search_service_name}.search.windows.net",
    index_name=azure_search_index_name,
    credential=AzureKeyCredential(azure_search_key),
    api_version=api_version
)

# Initialize embedding model
embedding_model = AzureOpenAIEmbeddings(
    azure_endpoint=azure_openai_endpoint,
    api_key=azure_openai_api_key,
    azure_deployment=azure_openai_deployment
)

def delete_index_if_exists():
    """Delete the index if it exists."""
    try:
        index_client.delete_index(azure_search_index_name)
        print(f"Index {azure_search_index_name} deleted")
        return True
    except Exception as e:
        print(f"Index delete error (might not exist): {str(e)}")
        return False

def create_search_index(force_recreate=False):
    """Create the search index with vector search capability."""
    if force_recreate:
        delete_index_if_exists()
    
    # Check if index exists already
    try:
        index_client.get_index(azure_search_index_name)
        print(f"Index {azure_search_index_name} already exists")
        if force_recreate:
            print("Forcing recreation of index...")
            delete_index_if_exists()
        else:
            return
    except Exception:
        print(f"Creating new index: {azure_search_index_name}")
    
    # Use HnswAlgorithmConfiguration directly instead of generic VectorSearchAlgorithmConfiguration
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="vector-config",
                parameters={
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine"
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="vector-profile",
                algorithm_configuration_name="vector-config"
            )
        ]
    )
    
    # Define the index fields
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="text", type=SearchFieldDataType.String),
        SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            vector_search_dimensions=1536,
            vector_search_profile_name="vector-profile"
        ),
        SimpleField(name="source", type=SearchFieldDataType.String),
        SimpleField(name="page", type=SearchFieldDataType.Int32)
    ]
    
    # Create the index
    index = SearchIndex(name=azure_search_index_name, fields=fields, vector_search=vector_search)
    
    try:
        index_client.create_or_update_index(index)
        print(f"Index {azure_search_index_name} created successfully")
    except Exception as e:
        print(f"Error creating index: {str(e)}")
        raise

def embed_and_index_pdf(pdf_path):
    """Extract text from PDF, generate embeddings, and index documents."""
    doc = fitz.open(pdf_path)
    documents = []
    filename = os.path.basename(pdf_path)
    # Replace periods with underscores to create valid document keys
    safe_filename = filename.replace(".", "_")
    
    print(f"Processing {filename}...")
    for page_num, page in enumerate(doc):
        text = page.get_text()
        embedding = embedding_model.embed_query(text)
        
        # Use field names that match the index schema
        document = {
            "id": f"{safe_filename}_{page_num}",  # Using safe_filename without periods
            "text": text,
            "embedding": embedding,
            "source": filename,
            "page": page_num
        }
        documents.append(document)
    
    print(f"Uploading {len(documents)} pages to Azure Cognitive Search...")
    try:
        search_client.upload_documents(documents)
        print("Upload completed successfully")
    except Exception as e:
        print(f"Error uploading documents: {str(e)}")
        raise

def search_vectors(query, top_k=3):
    """Search the vector index with the given query."""
    try:
        # Generate embedding for the query
        vector = embedding_model.embed_query(query)
        
        # Search using vector
        results = search_client.search(
            search_text=query,
            vector=vector,
            top_k=top_k,
            vector_fields="embedding",
            select=["text", "source", "page"]
        )
        
        return results
    except Exception as e:
        print(f"Error in vector search: {str(e)}")
        return []

if __name__ == "__main__":
    # Check for command line arguments
    force_recreate = False
    if len(sys.argv) > 1 and sys.argv[1] == "--force-recreate":
        force_recreate = True
    
    # First create the index with proper schema
    create_search_index(force_recreate=force_recreate)
    
    # Then upload documents
    embed_and_index_pdf("docs/bank_statement.pdf")
