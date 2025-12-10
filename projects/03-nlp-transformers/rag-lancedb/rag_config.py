"""
Hybrid RAG Configuration
Supports both local and ADLS storage for LanceDB

Part of: AI Architect Portfolio Project
Project: Month 2 Week 2 - RAG Systems with LanceDB
Date: December 2025

SECURITY: Uses environment variables for credentials
- Loads from .env file (NOT committed to Git)
- See .env.example for template
"""

import os
from dataclasses import dataclass
from typing import Optional, Literal
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    
    # Look for .env file in current directory and parent directories
    env_path = Path('.env')
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded credentials from {env_path.absolute()}")
    else:
        print("⚠️  No .env file found. Using environment variables or defaults.")
except ImportError:
    print("⚠️  python-dotenv not installed. Using environment variables only.")
    print("   Install with: pip install python-dotenv")


@dataclass
class RAGConfig:
    """
    Configuration for RAG system with hybrid storage support.
    
    Storage Modes:
    - 'local': Store vectors on local filesystem (good for learning/dev)
    - 'adls': Store vectors in Azure Data Lake Storage (production-like)
    """
    
    # ========================================================================
    # STORAGE CONFIGURATION
    # ========================================================================
    
    storage_backend: Literal['local', 'adls'] = 'local'
    """Storage backend: 'local' for development, 'adls' for production"""
    
    # Local storage settings
    local_db_path: str = "./lancedb"
    """Path for local LanceDB storage"""
    
    # ADLS storage settings
    adls_account_name: str = os.getenv("AZURE_STORAGE_ACCOUNT", "")
    """Azure Storage account name (from .env or environment)"""
    
    adls_account_key: str = os.getenv("AZURE_STORAGE_KEY", "")
    """Azure Storage account key (from .env or environment)"""
    
    adls_sas_token: str = os.getenv("AZURE_STORAGE_SAS_TOKEN", "")
    """Azure Storage SAS token (from .env or environment) - RECOMMENDED"""
    
    adls_container: str = os.getenv("AZURE_STORAGE_CONTAINER", "lancedb-vectors")
    """ADLS container name (from .env or environment)"""
    
    adls_path: str = "rag-system"
    """Path within container (e.g., 'rag-system' -> az://container/rag-system/)"""
    
    # ========================================================================
    # AZURE OPENAI CONFIGURATION
    # ========================================================================
    
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    """Azure OpenAI endpoint URL"""
    
    azure_openai_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    """Azure OpenAI API key"""
    
    embedding_deployment: str = "text-embedding-ada-002"
    """Embedding model deployment name"""
    
    llm_deployment: str = "gpt-4"
    """LLM deployment name for answer generation"""
    
    # ========================================================================
    # RAG SYSTEM CONFIGURATION
    # ========================================================================
    
    table_name: str = "documents"
    """LanceDB table name"""
    
    # Chunking settings
    chunk_size: int = 500
    """Words per chunk"""
    
    chunk_overlap: int = 50
    """Overlapping words between chunks"""
    
    # Retrieval settings
    top_k: int = 5
    """Number of chunks to retrieve"""
    
    # Generation settings
    temperature: float = 0.0
    """Temperature for LLM generation (0.0 = deterministic)"""
    
    max_tokens: int = 500
    """Maximum tokens in generated answer"""
    
    def get_storage_uri(self) -> str:
        """
        Get the storage URI based on backend type.
        
        Returns:
            Storage URI for LanceDB connection
        """
        if self.storage_backend == 'local':
            return self.local_db_path
        else:
            # ADLS URI format: az://container/path
            return f"az://{self.adls_container}/{self.adls_path}"
    
    def get_storage_options(self) -> Optional[dict]:
        """
        Get storage options for ADLS connection.
        
        Returns:
            Dict with ADLS credentials, or None for local storage
        """
        if self.storage_backend == 'local':
            return None
        
        options = {
            "account_name": self.adls_account_name
        }
        
        # Use SAS token if provided, otherwise use account key
        if self.adls_sas_token:
            options["sas_token"] = self.adls_sas_token
        elif self.adls_account_key:
            options["account_key"] = self.adls_account_key
        else:
            raise ValueError(
                "ADLS backend requires either account_key or sas_token. "
                "Set AZURE_STORAGE_KEY or AZURE_STORAGE_SAS_TOKEN environment variable."
            )
        
        return options
    
    def validate_adls_config(self) -> bool:
        """
        Validate ADLS configuration.
        
        Returns:
            True if ADLS config is valid
            
        Raises:
            ValueError if configuration is invalid
        """
        if self.storage_backend != 'adls':
            return True
        
        if not self.adls_account_name:
            raise ValueError(
                "ADLS account name required. "
                "Set AZURE_STORAGE_ACCOUNT environment variable."
            )
        
        if not self.adls_account_key and not self.adls_sas_token:
            raise ValueError(
                "ADLS credentials required. "
                "Set AZURE_STORAGE_KEY or AZURE_STORAGE_SAS_TOKEN environment variable."
            )
        
        if not self.adls_container:
            raise ValueError("ADLS container name required.")
        
        return True
    
    def print_config(self):
        """Print configuration summary."""
        print("\n" + "=" * 80)
        print("RAG SYSTEM CONFIGURATION")
        print("=" * 80)
        
        print(f"\n📁 STORAGE:")
        print(f"  Backend: {self.storage_backend.upper()}")
        
        if self.storage_backend == 'local':
            print(f"  Location: {self.local_db_path}")
        else:
            print(f"  Account: {self.adls_account_name}")
            print(f"  Container: {self.adls_container}")
            print(f"  Path: {self.adls_path}")
            print(f"  Full URI: {self.get_storage_uri()}")
        
        print(f"\n🤖 AZURE OPENAI:")
        if self.azure_openai_key:
            print(f"  Endpoint: {self.azure_openai_endpoint}")
            print(f"  Embedding Model: {self.embedding_deployment}")
            print(f"  LLM Model: {self.llm_deployment}")
        else:
            print("  Status: Using mock embeddings (no API key)")
        
        print(f"\n⚙️  RAG SETTINGS:")
        print(f"  Chunk Size: {self.chunk_size} words")
        print(f"  Chunk Overlap: {self.chunk_overlap} words")
        print(f"  Top K Retrieval: {self.top_k}")
        print(f"  Temperature: {self.temperature}")
        
        print("\n" + "=" * 80)


def create_local_config() -> RAGConfig:
    """
    Create configuration for local development.
    
    Returns:
        RAGConfig configured for local storage
    """
    return RAGConfig(
        storage_backend='local',
        local_db_path='./lancedb'
    )


def create_adls_config(
    account_name: Optional[str] = None,
    account_key: Optional[str] = None,
    container: Optional[str] = None,
    path: str = "rag-system"
) -> RAGConfig:
    """
    Create configuration for ADLS storage.
    
    Args:
        account_name: Azure Storage account name (or use env var)
        account_key: Azure Storage account key (or use env var)
        container: ADLS container name (or use env var)
        path: Path within container
        
    Returns:
        RAGConfig configured for ADLS storage
    """
    # Use provided container or fall back to environment variable
    container_name = container or os.getenv("AZURE_STORAGE_CONTAINER", "lancedb-vectors")
    
    config = RAGConfig(
        storage_backend='adls',
        adls_container=container_name,
        adls_path=path
    )
    
    # Override with provided values
    if account_name:
        config.adls_account_name = account_name
    if account_key:
        config.adls_account_key = account_key
    
    # Validate configuration
    config.validate_adls_config()
    
    return config


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("HYBRID RAG CONFIGURATION EXAMPLES")
    print("=" * 80)
    
    # Example 1: Local configuration
    print("\n1️⃣  LOCAL CONFIGURATION (Development)")
    print("─" * 80)
    local_config = create_local_config()
    local_config.print_config()
    
    # Example 2: ADLS configuration
    print("\n2️⃣  ADLS CONFIGURATION (Production)")
    print("─" * 80)
    print("Set environment variables first:")
    print("  export AZURE_STORAGE_ACCOUNT='mystorageaccount'")
    print("  export AZURE_STORAGE_KEY='your-key-here'")
    print()
    
    try:
        adls_config = create_adls_config()
        adls_config.print_config()
    except ValueError as e:
        print(f"⚠️  ADLS not configured: {e}")
        print("    (This is expected if you haven't set up ADLS yet)")
    
    # Example 3: Quick switching
    print("\n3️⃣  SWITCHING BETWEEN BACKENDS")
    print("─" * 80)
    print("""
# Start with local for learning
config = RAGConfig(storage_backend='local')

# Switch to ADLS for production
config = RAGConfig(storage_backend='adls')

# Or use helper functions
local_config = create_local_config()
adls_config = create_adls_config()
    """)
    
    print("\n✅ Configuration module ready!")
    print("   Use create_local_config() for development")
    print("   Use create_adls_config() for production")
