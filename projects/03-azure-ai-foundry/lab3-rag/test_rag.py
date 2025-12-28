"""Test RAG with real STIHL sales data"""

from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
import os

load_dotenv()

# Azure AI Search client
search_client = SearchClient(
    endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    index_name="stihl-sales-demo",
    credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
)

# Azure OpenAI client
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
    """Generate embedding for search query"""
    response = openai_client.embeddings.create(
        model="text-embedding-3-large",
        input=[text]
    )
    return response.data[0].embedding

def search(query: str, top_k: int = 3) -> list[dict]:
    """Search for relevant sales documents"""
    
    # Get query embedding
    query_vector = get_embedding(query)
    
    # Vector search
    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=top_k,
        fields="text_vector"
    )
    
    # Execute hybrid search (vector + keyword)
    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        top=top_k
    )
    
    return [dict(r) for r in results]

def rag_query(question: str) -> str:
    """RAG: Search + Generate"""
    
    print(f"\n🔍 Question: {question}")
    print("-" * 50)
    
    # 1. Search for relevant documents
    results = search(question, top_k=3)
    
    print(f"📄 Found {len(results)} relevant documents:")
    for r in results:
        print(f"   - {r['id']} ({r.get('category', 'N/A')}, {r.get('year_month', 'N/A')})")
    
    # 2. Build context from results
    context = "\n\n---\n\n".join([r['text_content'] for r in results])
    
    # 3. Generate grounded response
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """You are a STIHL Sales Analytics Expert. Answer questions using ONLY the provided sales data context.

Rules:
1. Base answers strictly on the provided context
2. Include specific numbers and percentages
3. If data is insufficient, say so
4. Structure responses with Key Finding, Data, Recommendation"""
            },
            {
                "role": "user",
                "content": f"""Context (Real Sales Data):
{context}

Question: {question}

Answer based on the data above:"""
            }
        ],
        temperature=0.3
    )
    
    return response.choices[0].message.content

# Test queries
if __name__ == "__main__":
    print("=" * 60)
    print("   STIHL Sales RAG Demo - Real Data!")
    print("=" * 60)
    
    # Test 1
    answer = rag_query("How did chainsaw sales perform in 2024?")
    print(f"\n💡 Answer:\n{answer}")
    
    print("\n" + "=" * 60)
    
    # Test 2
    answer = rag_query("Which products had the highest revenue?")
    print(f"\n💡 Answer:\n{answer}")
    
    print("\n" + "=" * 60)
    
    # Test 3
    answer = rag_query("Compare trimmer sales across different months")
    print(f"\n💡 Answer:\n{answer}")