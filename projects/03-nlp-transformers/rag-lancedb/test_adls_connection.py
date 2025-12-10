"""Test ADLS connection"""

import os
from dotenv import load_dotenv

# Load credentials
load_dotenv()

print("="*80)
print("TESTING ADLS CREDENTIALS")
print("="*80)

# Check environment variables
print("\n1️⃣  Checking environment variables...")
account = os.getenv("AZURE_STORAGE_ACCOUNT")
container = os.getenv("AZURE_STORAGE_CONTAINER")
sas_token = os.getenv("AZURE_STORAGE_SAS_TOKEN")

if account:
    print(f"✅ AZURE_STORAGE_ACCOUNT: {account}")
else:
    print("❌ AZURE_STORAGE_ACCOUNT not found")

if container:
    print(f"✅ AZURE_STORAGE_CONTAINER: {container}")
else:
    print("❌ AZURE_STORAGE_CONTAINER not found")

if sas_token:
    print(f"✅ AZURE_STORAGE_SAS_TOKEN: {'*' * 20}... (hidden)")
else:
    print("❌ AZURE_STORAGE_SAS_TOKEN not found")

# Test ADLS configuration
print("\n2️⃣  Testing ADLS configuration...")
try:
    from rag_config import create_adls_config
    
    config = create_adls_config()
    print(f"✅ ADLS config created successfully")
    print(f"   Account: {config.adls_account_name}")
    print(f"   Container: {config.adls_container}")
    print(f"   Storage URI: {config.get_storage_uri()}")
    
except Exception as e:
    print(f"❌ Error creating ADLS config: {e}")
    import traceback
    traceback.print_exc()

# Test LanceDB connection to ADLS
print("\n3️⃣  Testing LanceDB connection to ADLS...")
try:
    import lancedb
    import numpy as np
    
    uri = f"az://{container}/test-connection"
    storage_options = {
        "account_name": account,
        "sas_token": sas_token
    }
    
    print(f"   Connecting to: {uri}")
    print(f"   Using SAS token authentication")
    db = lancedb.connect(uri, storage_options=storage_options)
    print(f"✅ Connected to ADLS successfully!")
    
    # Create test table
    print("\n4️⃣  Creating test table in ADLS...")
    test_data = [{
        "id": "test1",
        "text": "Test document stored in Azure ADLS",
        "vector": np.random.randn(128).tolist()
    }]
    
    table = db.create_table("test_table", data=test_data, mode="overwrite")
    print(f"✅ Created test table in ADLS!")
    
    # Query test table
    print("\n5️⃣  Querying test table from ADLS...")
    query_vector = np.random.randn(128)
    results = table.search(query_vector).limit(1).to_list()
    print(f"✅ Query successful! Found {len(results)} results")
    print(f"   Result text: {results[0]['text']}")
    
    print("\n" + "="*80)
    print("🎉 SUCCESS! ADLS is fully configured and working!")
    print("="*80)
    print(f"\n📦 Your vectors are now stored in Azure:")
    print(f"   Account: {account}")
    print(f"   Container: {container}")
    print(f"   URL: https://{account}.blob.core.windows.net/{container}")
    print(f"\n💡 View in Azure Portal:")
    print(f"   Go to Storage Account -> Containers -> {container}")
    print(f"   You should see: test-connection/ folder")
    
except Exception as e:
    print(f"\n❌ Error connecting to ADLS: {e}")
    print("\n💡 Troubleshooting:")
    print("  1. Verify storage account 'azlancedb' exists in Azure Portal")
    print("  2. Verify container 'rag-container' exists")
    print("  3. Check SAS token is valid (expires 2027-01-01)")
    print("  4. Verify your IP address: 67.164.71.224")
    print("     Check current IP: curl ifconfig.me")
    print("  5. Ensure adlfs is installed: pip install adlfs")
    print("\n🔍 Full error details:")
    import traceback
    traceback.print_exc()