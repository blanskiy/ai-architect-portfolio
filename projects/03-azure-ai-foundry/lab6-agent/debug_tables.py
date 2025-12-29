"""Debug script to check actual Databricks table schemas"""

import os
from dotenv import load_dotenv
from databricks import sql as databricks_sql

load_dotenv()

DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_CATALOG = os.getenv("DATABRICKS_CATALOG", "ai_systems")

def get_connection():
    return databricks_sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
        catalog=DATABRICKS_CATALOG
    )

def check_tables():
    conn = get_connection()
    cursor = conn.cursor()
    
    tables = [
        f"{DATABRICKS_CATALOG}.stihl_gold.monthly_trends",
        f"{DATABRICKS_CATALOG}.stihl_gold.product_performance",
        f"{DATABRICKS_CATALOG}.stihl_silver.fact_sales"
    ]
    
    for table in tables:
        print(f"\n{'='*60}")
        print(f"TABLE: {table}")
        print('='*60)
        
        try:
            # Get schema
            cursor.execute(f"DESCRIBE {table}")
            print("\nCOLUMNS:")
            for row in cursor.fetchall():
                print(f"  {row[0]:<25} {row[1]}")
            
            # Get sample data
            cursor.execute(f"SELECT * FROM {table} LIMIT 3")
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            print(f"\nSAMPLE DATA ({len(rows)} rows):")
            print(f"  {columns}")
            for row in rows:
                print(f"  {row}")
                
        except Exception as e:
            print(f"  ERROR: {e}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_tables()