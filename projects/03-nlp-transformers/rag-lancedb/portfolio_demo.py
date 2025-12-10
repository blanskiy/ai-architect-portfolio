"""
Portfolio Demo: Hybrid RAG System with Azure ADLS
Part of AI Architect Portfolio - Month 2 Week 2

This demo showcases:
- Cloud-native RAG architecture
- Azure Data Lake Storage integration
- Semantic search with vector embeddings
- Document Q&A with source citations
"""

from rag_config import create_adls_config
from hybrid_rag_system import HybridRAGSystem

print("="*80)
print("PORTFOLIO DEMO: HYBRID RAG SYSTEM WITH AZURE ADLS")
print("="*80)

# Initialize RAG system with Azure ADLS
print("\n📊 Initializing cloud-native RAG system...")
config = create_adls_config()
rag = HybridRAGSystem(config)

# Sample knowledge base - AI/ML topics
documents = [
    {
        'text': """
        Azure AI Services provide comprehensive artificial intelligence capabilities.
        Azure OpenAI Service offers access to GPT-4, GPT-3.5, and embeddings models.
        These can be used for chatbots, content generation, code assistance, and document analysis.
        The service includes built-in content filtering and responsible AI features.
        Pricing is based on tokens processed, with different rates for different models.
        """,
        'metadata': {
            'source': 'azure_ai_overview.txt',
            'category': 'azure',
            'topic': 'ai-services'
        }
    },
    {
        'text': """
        LanceDB is a lightweight embedded vector database built on Apache Arrow.
        It provides fast vector search without requiring a separate server.
        LanceDB supports both local filesystem and cloud storage like Azure ADLS.
        The database uses the Lance format for efficient storage and retrieval.
        Perfect for RAG systems, semantic search, and recommendation engines.
        """,
        'metadata': {
            'source': 'lancedb_intro.txt',
            'category': 'databases',
            'topic': 'vector-databases'
        }
    },
    {
        'text': """
        Retrieval-Augmented Generation (RAG) combines information retrieval with LLMs.
        The system retrieves relevant documents from a knowledge base.
        These documents provide context to the language model for generating answers.
        RAG solves the problem of LLM knowledge cutoffs and hallucinations.
        It enables LLMs to answer questions based on private or up-to-date data.
        """,
        'metadata': {
            'source': 'rag_explained.txt',
            'category': 'ai',
            'topic': 'rag-systems'
        }
    },
    {
        'text': """
        Vector embeddings convert text into high-dimensional numerical representations.
        Similar meanings result in similar vectors, enabling semantic search.
        Azure OpenAI's text-embedding-ada-002 produces 1536-dimensional vectors.
        Cosine similarity measures how closely related two vectors are.
        This enables finding relevant documents based on meaning, not just keywords.
        """,
        'metadata': {
            'source': 'embeddings_guide.txt',
            'category': 'ai',
            'topic': 'embeddings'
        }
    }
]

# Ingest documents to Azure ADLS
print("\n📤 Ingesting knowledge base to Azure ADLS...")
rag.ingest_documents(documents)

# Demo queries
queries = [
    "What is Azure OpenAI Service and what models does it offer?",
    "How does LanceDB support cloud storage?",
    "Explain how RAG works and what problem it solves",
    "What are vector embeddings and how are they used for search?"
]

print("\n" + "="*80)
print("DEMO QUERIES - CLOUD-NATIVE RAG IN ACTION")
print("="*80)

for i, question in enumerate(queries, 1):
    print(f"\n{'─'*80}")
    print(f"Query {i}: {question}")
    print("─"*80)
    
    result = rag.query(question, top_k=3)
    
    print(f"\n📝 Answer:")
    print(f"   {result['answer'][:200]}...")
    
    print(f"\n📚 Sources used: {result['num_sources_used']} documents")
    print(f"💾 Storage: {result['storage_backend'].upper()} (Azure ADLS)")
    
    if result['sources']:
        print(f"\n🔗 Source details:")
        for idx, source in enumerate(result['sources'][:2], 1):
            metadata = source['metadata']
            print(f"   [{idx}] {metadata.get('source', 'Unknown')}")
            print(f"       Category: {metadata.get('category', 'N/A')}")
            print(f"       Similarity: {source.get('similarity', 0):.3f}")

# System statistics
print("\n" + "="*80)
print("SYSTEM STATISTICS")
print("="*80)

stats = rag.get_stats()
print(f"\n📊 Performance:")
print(f"   Documents ingested: {stats['documents_ingested']}")
print(f"   Storage backend: {stats['storage_backend'].upper()}")
print(f"   Chunk size: {stats['config']['chunk_size']} words")
print(f"   Chunk overlap: {stats['config']['chunk_overlap']} words")
print(f"   Retrieval: Top-{stats['config']['top_k']} most relevant")

print(f"\n☁️  Cloud Architecture:")
print(f"   Account: azlancedb")
print(f"   Container: rag-container")
print(f"   Path: rag-system")
print(f"   URL: https://azlancedb.blob.core.windows.net/rag-container")

print("\n" + "="*80)
print("✅ DEMO COMPLETE!")
print("="*80)

print("""
🎯 Key Accomplishments:
   ✓ Built cloud-native RAG system
   ✓ Integrated with Azure Data Lake Storage
   ✓ Implemented semantic search with vector embeddings
   ✓ Demonstrated separation of compute and storage
   ✓ Provided source citations for transparency
   ✓ Used secure credential management

📚 Technologies Used:
   • Azure Data Lake Storage Gen2 (cloud storage)
   • LanceDB (vector database)
   • Python-dotenv (secure credentials)
   • NumPy (vector operations)
   • Azure OpenAI (embeddings)

🔗 Portfolio Links:
   • GitHub: [Your Repository]
   • Documentation: README_HYBRID.md
   • Security Guide: SECURITY_GUIDE.md
   • ADLS Setup: ADLS_SETUP_GUIDE.md
""")
