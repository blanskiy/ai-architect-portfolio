"""Upload real STIHL sales data from Databricks export"""

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
import pandas as pd
import os
import glob

load_dotenv()

# Azure AI Search client
search_client = SearchClient(
    endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    index_name="stihl-sales-demo",
    credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
)

# Azure OpenAI client for embeddings
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default"
)

openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_ad_token_provider=token_provider,
    api_version="2024-10-21"
)

def get_embedding(text: str) -> list[float]:
    """Generate embedding using Azure OpenAI"""
    response = openai_client.embeddings.create(
        model="text-embedding-3-large",
        input=[text[:8000]]
    )
    return response.data[0].embedding

def upload_documents():
    # Find CSV file
    csv_files = glob.glob("*.csv")
    if not csv_files:
        print("ERROR: No CSV file found in current directory")
        return
    
    csv_file = csv_files[0]
    print(f"Loading data from: {csv_file}")
    
    # Load CSV
    df = pd.read_csv(csv_file)
    print(f"Loaded {len(df)} records")
    print(f"Columns: {list(df.columns)}")
    
    # Convert to list of dicts
    documents = df.to_dict('records')
    
    # Process each document
    print(f"\nProcessing {len(documents)} documents...")
    
    for i, doc in enumerate(documents):
        print(f"  [{i+1}/{len(documents)}] Embedding: {doc['id'][:40]}...")
        
        # Generate embedding from text_content
        doc['text_vector'] = get_embedding(str(doc['text_content']))
        
        # Ensure correct types for Azure Search
        doc['total_units'] = int(doc['total_units']) if pd.notna(doc.get('total_units')) else 0
        doc['total_revenue'] = float(doc['total_revenue']) if pd.notna(doc.get('total_revenue')) else 0.0
        doc['product_id'] = str(doc.get('product_id', ''))
        doc['category'] = str(doc.get('category', ''))
        doc['year_month'] = str(doc.get('year_month', ''))
    
    print("\nUploading to Azure AI Search...")
    result = search_client.upload_documents(documents)
    
    success_count = sum(1 for r in result if r.succeeded)
    print(f"✓ Uploaded {success_count}/{len(documents)} documents!")

if __name__ == "__main__":
    upload_documents()