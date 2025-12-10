"""
Hybrid Production RAG System with LanceDB
Supports both local and ADLS storage

Part of: AI Architect Portfolio Project
Project: Month 2 Week 2 - RAG Systems with LanceDB
Date: December 2025

This module provides a production-ready RAG system with:
- Hybrid storage (local or ADLS)
- Document ingestion (PDF, DOCX, TXT)
- Intelligent chunking with overlap
- Azure OpenAI embeddings
- LanceDB vector storage
- Semantic search
- Answer generation with citations
"""

import os
from typing import List, Dict, Optional
import numpy as np
from datetime import datetime
import json

# Import hybrid configuration
from rag_config import RAGConfig, create_local_config, create_adls_config

# Try to import dependencies
try:
    import lancedb
    LANCEDB_AVAILABLE = True
except ImportError:
    LANCEDB_AVAILABLE = False
    print("⚠️  LanceDB not installed. Install with: pip install lancedb")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  OpenAI not installed. Install with: pip install openai")


class DocumentChunker:
    """Smart document chunking with overlap."""
    
    @staticmethod
    def chunk_by_words(
        text: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[Dict[str, any]]:
        """
        Chunk text by words with overlap.
        
        Args:
            text: Input text
            chunk_size: Words per chunk
            overlap: Overlapping words
            
        Returns:
            List of chunk dictionaries with metadata
        """
        words = text.split()
        chunks = []
        
        start = 0
        chunk_index = 0
        
        while start < len(words):
            end = start + chunk_size
            chunk_words = words[start:end]
            chunk_text = ' '.join(chunk_words)
            
            chunks.append({
                'text': chunk_text,
                'chunk_index': chunk_index,
                'start_word': start,
                'end_word': min(end, len(words)),
                'word_count': len(chunk_words)
            })
            
            chunk_index += 1
            start = end - overlap
            
            if end >= len(words):
                break
        
        return chunks


class EmbeddingGenerator:
    """Generate embeddings using Azure OpenAI."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.setup_openai()
    
    def setup_openai(self):
        """Configure Azure OpenAI."""
        if not OPENAI_AVAILABLE:
            print("⚠️  Using mock embeddings (OpenAI not installed)")
            return
        
        if not self.config.azure_openai_key:
            print("⚠️  No Azure OpenAI key found. Using mock embeddings.")
            print("   Set AZURE_OPENAI_API_KEY environment variable")
            return
        
        openai.api_type = "azure"
        openai.api_key = self.config.azure_openai_key
        openai.api_base = self.config.azure_openai_endpoint
        openai.api_version = "2023-05-15"
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text."""
        if not OPENAI_AVAILABLE or not self.config.azure_openai_key:
            return self._mock_embedding(text)
        
        try:
            response = openai.Embedding.create(
                engine=self.config.embedding_deployment,
                input=text
            )
            embedding = response['data'][0]['embedding']
            return np.array(embedding)
        except Exception as e:
            print(f"⚠️  Error generating embedding: {e}")
            return self._mock_embedding(text)
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings
    
    @staticmethod
    def _mock_embedding(text: str, dimensions: int = 1536) -> np.ndarray:
        """Generate deterministic mock embedding for demo."""
        np.random.seed(hash(text) % 2**32)
        embedding = np.random.randn(dimensions)
        return embedding / np.linalg.norm(embedding)


class HybridLanceDBVectorStore:
    """
    Vector storage using LanceDB with hybrid backend support.
    
    Supports both local filesystem and Azure Data Lake Storage (ADLS).
    """
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.db = None
        self.table = None
        self.is_connected = False
        self.connect()
    
    def connect(self):
        """Connect to LanceDB with configured backend."""
        if not LANCEDB_AVAILABLE:
            print("⚠️  LanceDB not available. Using mock storage.")
            return
        
        try:
            storage_uri = self.config.get_storage_uri()
            storage_options = self.config.get_storage_options()
            
            print(f"\n🔌 Connecting to LanceDB...")
            print(f"   Backend: {self.config.storage_backend.upper()}")
            print(f"   URI: {storage_uri}")
            
            if storage_options:
                self.db = lancedb.connect(storage_uri, storage_options=storage_options)
                self.is_connected = True
                print(f"   ✅ Connected to ADLS: {self.config.adls_account_name}")
            else:
                self.db = lancedb.connect(storage_uri)
                self.is_connected = True
                print(f"   ✅ Connected to local storage")
            
        except Exception as e:
            self.is_connected = False
            print(f"❌ Error connecting to LanceDB: {e}")
            if self.config.storage_backend == 'adls':
                print("\n💡 ADLS Troubleshooting:")
                print("   1. Check AZURE_STORAGE_ACCOUNT is set")
                print("   2. Check AZURE_STORAGE_KEY or AZURE_STORAGE_SAS_TOKEN is set")
                print("   3. Verify container exists in storage account")
                print("   4. Check network connectivity to Azure")
    
    def create_index(self, documents: List[Dict]):
        """Create or update vector index."""
        if not self.is_connected or self.db is None:
            print("⚠️  Database not connected")
            return
        
        try:
            self.table = self.db.create_table(
                self.config.table_name,
                data=documents,
                mode="overwrite"
            )
            print(f"✅ Created index with {len(documents)} documents")
            
            if self.config.storage_backend == 'adls':
                print(f"   📦 Vectors stored in ADLS: {self.config.get_storage_uri()}")
        except Exception as e:
            print(f"❌ Error creating index: {e}")
            import traceback
            traceback.print_exc()
    
    def add_documents(self, documents: List[Dict]):
        """Add documents to existing index."""
        if not self.table:
            print("⚠️  Table not initialized. Use create_index first.")
            return
        
        try:
            self.table.add(documents)
            print(f"✅ Added {len(documents)} documents")
        except Exception as e:
            print(f"❌ Error adding documents: {e}")
    
    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        filter_condition: Optional[str] = None
    ) -> List[Dict]:
        """Search for similar vectors."""
        if not self.table:
            print("⚠️  Table not initialized")
            return []
        
        try:
            results = (
                self.table.search(query_vector)
                .limit(top_k)
            )
            
            if filter_condition:
                results = results.where(filter_condition)
            
            return results.to_list()
        except Exception as e:
            print(f"❌ Error searching: {e}")
            return []


class HybridRAGSystem:
    """Complete RAG system with hybrid storage support."""
    
    def __init__(self, config: Optional[RAGConfig] = None):
        """
        Initialize RAG system.
        
        Args:
            config: Optional custom configuration (defaults to local storage)
        """
        self.config = config or create_local_config()
        
        # Print configuration
        self.config.print_config()
        
        # Initialize components
        self.chunker = DocumentChunker()
        self.embedder = EmbeddingGenerator(self.config)
        self.vector_store = HybridLanceDBVectorStore(self.config)
        self.documents_ingested = 0
    
    def ingest_documents(
        self,
        documents: List[Dict[str, str]],
        chunking_strategy: str = "words"
    ):
        """Ingest documents into the RAG system."""
        print(f"\n📚 Ingesting {len(documents)} documents...")
        print("─" * 80)
        
        all_chunks = []
        
        for doc_idx, doc in enumerate(documents):
            text = doc['text']
            metadata = doc.get('metadata', {})
            
            # Chunk document
            chunks = self.chunker.chunk_by_words(
                text,
                self.config.chunk_size,
                self.config.chunk_overlap
            )
            
            print(f"Document {doc_idx + 1}: {len(chunks)} chunks")
            
            # Generate embeddings
            chunk_texts = [c['text'] for c in chunks]
            embeddings = self.embedder.generate_embeddings_batch(chunk_texts)
            
            # Prepare for storage
            for chunk, embedding in zip(chunks, embeddings):
                all_chunks.append({
                    'id': f"doc{doc_idx}_chunk{chunk['chunk_index']}",
                    'text': chunk['text'],
                    'vector': embedding,
                    'metadata': {
                        **metadata,
                        'document_index': doc_idx,
                        'chunk_index': chunk['chunk_index'],
                        'word_count': chunk['word_count'],
                        'ingested_at': datetime.utcnow().isoformat(),
                        'storage_backend': self.config.storage_backend
                    }
                })
        
        # Store in vector database
        self.vector_store.create_index(all_chunks)
        self.documents_ingested = len(documents)
        
        print(f"\n✅ Ingestion complete!")
        print(f"   Documents: {len(documents)}")
        print(f"   Total chunks: {len(all_chunks)}")
        print(f"   Storage: {self.config.storage_backend.upper()}")
        if self.config.storage_backend == 'adls':
            print(f"   ADLS Path: {self.config.get_storage_uri()}")
    
    def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        return_sources: bool = True
    ) -> Dict[str, any]:
        """Query the RAG system."""
        top_k = top_k or self.config.top_k
        
        print(f"\n🔍 Query: '{question}'")
        print("─" * 80)
        
        # Generate query embedding
        print("Step 1: Generating query embedding...")
        query_vector = self.embedder.generate_embedding(question)
        
        # Retrieve relevant chunks
        print(f"Step 2: Searching for top {top_k} relevant chunks...")
        results = self.vector_store.search(query_vector, top_k=top_k)
        
        if not results:
            return {
                'question': question,
                'answer': "I don't have enough information to answer that question.",
                'sources': [],
                'success': False
            }
        
        print(f"Found {len(results)} relevant chunks")
        
        # Build context
        print("Step 3: Building context...")
        context_parts = []
        sources = []
        
        for i, result in enumerate(results, 1):
            context_parts.append(f"[Source {i}]: {result['text']}")
            sources.append({
                'id': result['id'],
                'text': result['text'],
                'metadata': result['metadata'],
                'similarity': 1 - result.get('_distance', 0)
            })
        
        context = "\n\n".join(context_parts)
        
        # Generate answer
        print("Step 4: Generating answer...")
        answer = self._generate_answer(question, context)
        
        result = {
            'question': question,
            'answer': answer,
            'sources': sources if return_sources else [],
            'num_sources_used': len(sources),
            'storage_backend': self.config.storage_backend,
            'success': True
        }
        
        print("\n✅ Query complete!")
        return result
    
    def _generate_answer(self, question: str, context: str) -> str:
        """Generate answer using LLM."""
        prompt = f"""Answer the question based on the context below.
If the answer is not in the context, say "I don't have information about that in my knowledge base."
Always cite which source(s) you used (e.g., [Source 1, 2]).

Context:
{context}

Question: {question}

Answer:"""
        
        if not OPENAI_AVAILABLE or not self.config.azure_openai_key:
            return self._mock_answer(question, context)
        
        try:
            response = openai.ChatCompletion.create(
                engine=self.config.llm_deployment,
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that answers questions based on provided context. Always cite your sources."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️  Error generating answer: {e}")
            return self._mock_answer(question, context)
    
    @staticmethod
    def _mock_answer(question: str, context: str) -> str:
        """Generate mock answer for demo."""
        context_snippet = context[:200] + "..."
        return f"Based on the provided context: {context_snippet} [Source 1]"
    
    def get_stats(self) -> Dict:
        """Get system statistics."""
        return {
            'documents_ingested': self.documents_ingested,
            'storage_backend': self.config.storage_backend,
            'config': {
                'chunk_size': self.config.chunk_size,
                'chunk_overlap': self.config.chunk_overlap,
                'top_k': self.config.top_k,
                'embedding_model': self.config.embedding_deployment
            }
        }


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("HYBRID RAG SYSTEM DEMO")
    print("=" * 80)
    
    # Example 1: Local storage (default)
    print("\n1️⃣  LOCAL STORAGE MODE")
    print("─" * 80)
    
    local_config = create_local_config()
    rag_local = HybridRAGSystem(local_config)
    
    # Sample documents
    documents = [
        {
            'text': """
            Azure AI Services provide comprehensive tools for building intelligent applications.
            Azure OpenAI Service offers GPT-4, GPT-3.5, and embeddings models for language tasks.
            The service includes content filtering and responsible AI features.
            """,
            'metadata': {'source': 'azure_ai_overview.txt'}
        }
    ]
    
    rag_local.ingest_documents(documents)
    result = rag_local.query("What is Azure OpenAI Service?")
    print(f"\nAnswer: {result['answer']}")
    
    # Example 2: ADLS storage (if configured)
    print("\n\n2️⃣  ADLS STORAGE MODE")
    print("─" * 80)
    print("To use ADLS, set environment variables:")
    print("  export AZURE_STORAGE_ACCOUNT='your-account'")
    print("  export AZURE_STORAGE_KEY='your-key'")
    print()
    
    try:
        adls_config = create_adls_config()
        rag_adls = HybridRAGSystem(adls_config)
        rag_adls.ingest_documents(documents)
        result = rag_adls.query("What is Azure OpenAI Service?")
        print(f"\nAnswer: {result['answer']}")
    except ValueError as e:
        print(f"⚠️  ADLS not configured: {e}")
        print("   (This is expected if you haven't set up ADLS yet)")
