"""Create Azure AI Search index for STIHL sales data"""

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SearchableField,
    SimpleField,
)
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import os

load_dotenv()

# Configuration
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = "stihl-sales-demo"

print(f"Creating index '{INDEX_NAME}' at {SEARCH_ENDPOINT}")

# Create client
index_client = SearchIndexClient(
    endpoint=SEARCH_ENDPOINT,
    credential=AzureKeyCredential(SEARCH_KEY)
)

# Define fields
fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
    SearchableField(name="text_content", type=SearchFieldDataType.String),
    SearchableField(name="product_id", type=SearchFieldDataType.String, filterable=True),
    SearchableField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
    SearchableField(name="year_month", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="total_units", type=SearchFieldDataType.Int64),
    SimpleField(name="total_revenue", type=SearchFieldDataType.Double),
    # Vector field for embeddings (3072 dimensions for text-embedding-3-large)
    SearchField(
        name="text_vector",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=3072,
        vector_search_profile_name="vector-profile"
    ),
]

# Vector search configuration
vector_search = VectorSearch(
    algorithms=[HnswAlgorithmConfiguration(name="hnsw-config")],
    profiles=[VectorSearchProfile(name="vector-profile", algorithm_configuration_name="hnsw-config")]
)

# Create index
index = SearchIndex(name=INDEX_NAME, fields=fields, vector_search=vector_search)

# Delete if exists, then create
try:
    index_client.delete_index(INDEX_NAME)
    print(f"Deleted existing index: {INDEX_NAME}")
except:
    pass

result = index_client.create_index(index)
print(f"✓ Created index: {result.name}")