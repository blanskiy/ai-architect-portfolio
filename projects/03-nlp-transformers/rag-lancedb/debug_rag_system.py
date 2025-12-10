"""
Debug script to test hybrid RAG system flow
"""

import os
from dotenv import load_dotenv
import numpy as np

# Load credentials
load_dotenv()

print("="*80)
print("DEBUGGING HYBRID RAG SYSTEM")
print("="*80)

# Step 1: Test imports
print("\n1️⃣  Testing imports...")
try:
    import lancedb
    print("✅ lancedb imported successfully")
except ImportError as e:
    print(f"❌ lancedb import failed: {e}")
    exit(1)

# Step 2: Test configuration
print("\n2️⃣  Testing configuration...")
try:
    from rag_config import create_adls_config
    config = create_adls_config()
    print(f"✅ Config created")
    print(f"   Account: {config.adls_account_name}")
    print(f"   Container: {config.adls_container}")
    print(f"   SAS token present: {bool(config.adls_sas_token)}")
except Exception as e:
    print(f"❌ Config failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 3: Test connection
print("\n3️⃣  Testing LanceDB connection...")
try:
    storage_uri = config.get_storage_uri()
    storage_options = config.get_storage_options()
    
    print(f"   URI: {storage_uri}")
    print(f"   Has storage options: {storage_options is not None}")
    
    db = lancedb.connect(storage_uri, storage_options=storage_options)
    print(f"✅ Connected successfully")
    print(f"   DB object type: {type(db)}")
    print(f"   DB is None: {db is None}")
    print(f"   DB is truthy: {bool(db)}")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 4: Test table creation
print("\n4️⃣  Testing table creation...")
try:
    test_data = [{
        'id': 'test1',
        'text': 'Test document',
        'vector': np.random.randn(128).tolist(),
        'metadata': {'source': 'test'}
    }]
    
    print(f"   Creating table 'debug_test'...")
    table = db.create_table("debug_test", data=test_data, mode="overwrite")
    print(f"✅ Table created successfully!")
    print(f"   Table object type: {type(table)}")
    
    # Test query
    print("\n5️⃣  Testing query...")
    query_vector = np.random.randn(128)
    results = table.search(query_vector).limit(1).to_list()
    print(f"✅ Query successful! Found {len(results)} results")
    
    print("\n" + "="*80)
    print("🎉 ALL TESTS PASSED!")
    print("="*80)
    print("\nThe hybrid RAG system should work now.")
    print("If hybrid_rag_system.py still fails, there may be an issue with")
    print("how the HybridLanceDBVectorStore class checks the db object.")
    
except Exception as e:
    print(f"❌ Table creation failed: {e}")
    import traceback
    traceback.print_exc()
    
    print("\n💡 This is the same error happening in hybrid_rag_system.py")
    print("   Check:")
    print("   1. SAS token has write permissions (racwdlmeo)")
    print("   2. Container 'rag-container' exists")
    print("   3. IP address matches: 67.164.71.224")
