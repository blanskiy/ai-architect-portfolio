"""
Sample Data Generator
Generate sample data for testing the feature store.

Creates:
- Raw transactions
- User profiles
- Product catalog
- Labels for training
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import random


def generate_sample_data(
    output_dir: str = "data",
    n_users: int = 100,
    n_products: int = 50,
    n_stores: int = 10,
    n_transactions: int = 1000,
    seed: int = 42,
):
    """
    Generate sample data for the feature store.
    
    Args:
        output_dir: Directory to save data files
        n_users: Number of users
        n_products: Number of products
        n_stores: Number of stores
        n_transactions: Number of transactions
        seed: Random seed for reproducibility
    """
    
    np.random.seed(seed)
    random.seed(seed)
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Generate date range (last 90 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    # ==========================================================================
    # Generate Users
    # ==========================================================================
    print("Generating users...")
    
    user_ids = [f"user_{i:04d}" for i in range(n_users)]
    
    user_profiles = pd.DataFrame({
        "user_id": user_ids,
        "event_timestamp": [end_date] * n_users,
        "created_timestamp": [datetime.now()] * n_users,
        "account_age_days": np.random.randint(30, 1000, n_users),
        "is_premium_member": np.random.choice([True, False], n_users, p=[0.2, 0.8]),
        "preferred_category": np.random.choice(
            ["Chainsaws", "Trimmers", "Blowers", "Mowers", "Accessories"],
            n_users
        ),
        "home_store_id": np.random.choice([f"store_{i:03d}" for i in range(n_stores)], n_users),
        "email_opt_in": np.random.choice([True, False], n_users, p=[0.6, 0.4]),
    })
    
    user_profiles.to_parquet(output_path / "user_profiles.parquet", index=False)
    print(f"  Saved {len(user_profiles)} user profiles")
    
    # ==========================================================================
    # Generate Products
    # ==========================================================================
    print("Generating products...")
    
    product_ids = [f"product_{i:04d}" for i in range(n_products)]
    
    categories = ["Chainsaws", "Trimmers", "Blowers", "Mowers", "Accessories"]
    subcategories = {
        "Chainsaws": ["Gas", "Electric", "Battery"],
        "Trimmers": ["Gas", "Electric", "Battery"],
        "Blowers": ["Handheld", "Backpack"],
        "Mowers": ["Walk-Behind", "Zero-Turn"],
        "Accessories": ["Chains", "Oil", "Safety Gear"],
    }
    
    products_data = []
    for pid in product_ids:
        category = random.choice(categories)
        price = np.random.uniform(50, 800) if category != "Accessories" else np.random.uniform(10, 100)
        cost = price * np.random.uniform(0.4, 0.6)
        
        products_data.append({
            "product_id": pid,
            "event_timestamp": end_date,
            "created_timestamp": datetime.now(),
            "product_name": f"{category} Model {pid[-3:]}",
            "category": category,
            "subcategory": random.choice(subcategories[category]),
            "price": round(price, 2),
            "cost": round(cost, 2),
            "margin_pct": round((price - cost) / price * 100, 1),
            "weight_lbs": np.random.uniform(5, 30) if category != "Accessories" else np.random.uniform(0.5, 5),
            "is_seasonal": random.choice([True, False]),
        })
    
    products_df = pd.DataFrame(products_data)
    products_df.to_parquet(output_path / "products.parquet", index=False)
    print(f"  Saved {len(products_df)} products")
    
    # ==========================================================================
    # Generate Stores
    # ==========================================================================
    print("Generating stores...")
    
    store_ids = [f"store_{i:03d}" for i in range(n_stores)]
    regions = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]
    states = ["NY", "FL", "TX", "CA", "WA", "CO", "GA", "IL", "PA", "OH"]
    
    stores_df = pd.DataFrame({
        "store_id": store_ids,
        "event_timestamp": [end_date] * n_stores,
        "created_timestamp": [datetime.now()] * n_stores,
        "store_name": [f"STIHL Dealer {i:03d}" for i in range(n_stores)],
        "store_type": np.random.choice(["Dealer", "Retail", "Online"], n_stores, p=[0.6, 0.3, 0.1]),
        "region": np.random.choice(regions, n_stores),
        "state": np.random.choice(states, n_stores),
        "avg_transaction_value": np.random.uniform(100, 400, n_stores),
        "monthly_sales_volume": np.random.uniform(50000, 500000, n_stores),
        "customer_count": np.random.randint(100, 5000, n_stores),
    })
    
    stores_df.to_parquet(output_path / "stores.parquet", index=False)
    print(f"  Saved {len(stores_df)} stores")
    
    # ==========================================================================
    # Generate Transactions
    # ==========================================================================
    print("Generating transactions...")
    
    transactions_data = []
    for i in range(n_transactions):
        # Random timestamp in the last 90 days
        days_ago = np.random.randint(0, 90)
        hours_ago = np.random.randint(0, 24)
        txn_date = end_date - timedelta(days=days_ago, hours=hours_ago)
        
        user_id = random.choice(user_ids)
        product_id = random.choice(product_ids)
        store_id = random.choice(store_ids)
        
        # Amount based on product price (with some variation)
        base_price = products_df[products_df['product_id'] == product_id]['price'].values[0]
        amount = base_price * np.random.uniform(0.9, 1.1)  # ±10% variation
        
        transactions_data.append({
            "transaction_id": f"txn_{i:06d}",
            "user_id": user_id,
            "product_id": product_id,
            "store_id": store_id,
            "transaction_date": txn_date,
            "amount": round(amount, 2),
            "quantity": np.random.randint(1, 3),
        })
    
    transactions_df = pd.DataFrame(transactions_data)
    
    # Save as both raw and feature-store format
    transactions_df.to_parquet(output_path / "raw_transactions.parquet", index=False)
    print(f"  Saved {len(transactions_df)} raw transactions")
    
    # ==========================================================================
    # Generate Product Views (for product stats)
    # ==========================================================================
    print("Generating product views...")
    
    views_data = []
    for i in range(n_transactions * 5):  # 5x more views than purchases
        days_ago = np.random.randint(0, 30)
        view_date = end_date - timedelta(days=days_ago)
        
        views_data.append({
            "view_id": f"view_{i:06d}",
            "user_id": random.choice(user_ids),
            "product_id": random.choice(product_ids),
            "view_date": view_date,
        })
    
    views_df = pd.DataFrame(views_data)
    views_df.to_parquet(output_path / "product_views.parquet", index=False)
    print(f"  Saved {len(views_df)} product views")
    
    # ==========================================================================
    # Generate Product Ratings
    # ==========================================================================
    print("Generating product ratings...")
    
    ratings_data = []
    for i in range(n_transactions // 3):  # 1/3 of transactions get rated
        ratings_data.append({
            "rating_id": f"rating_{i:06d}",
            "user_id": random.choice(user_ids),
            "product_id": random.choice(product_ids),
            "rating": np.random.randint(3, 6),  # 3-5 stars
            "rating_date": end_date - timedelta(days=np.random.randint(0, 90)),
        })
    
    ratings_df = pd.DataFrame(ratings_data)
    ratings_df.to_parquet(output_path / "product_ratings.parquet", index=False)
    print(f"  Saved {len(ratings_df)} ratings")
    
    # ==========================================================================
    # Generate Product Inventory
    # ==========================================================================
    print("Generating inventory...")
    
    inventory_df = pd.DataFrame({
        "product_id": product_ids,
        "quantity": np.random.randint(0, 500, n_products),
        "last_updated": [end_date] * n_products,
    })
    
    inventory_df.to_parquet(output_path / "inventory.parquet", index=False)
    print(f"  Saved {len(inventory_df)} inventory records")
    
    # ==========================================================================
    # Generate Labels for Training
    # ==========================================================================
    print("Generating training labels...")
    
    # Sample users and create labels for "will purchase in next 7 days"
    labels_data = []
    for user_id in user_ids:
        # Create label at different points in time
        for days_back in [30, 60, 90]:
            label_date = end_date - timedelta(days=days_back)
            
            # Check if user purchased in the 7 days after label_date
            user_txns = transactions_df[transactions_df['user_id'] == user_id]
            future_txns = user_txns[
                (user_txns['transaction_date'] > label_date) &
                (user_txns['transaction_date'] <= label_date + timedelta(days=7))
            ]
            
            labels_data.append({
                "user_id": user_id,
                "event_timestamp": label_date,
                "label": 1 if len(future_txns) > 0 else 0,
            })
    
    labels_df = pd.DataFrame(labels_data)
    labels_df.to_parquet(output_path / "labels.parquet", index=False)
    print(f"  Saved {len(labels_df)} training labels")
    
    print("\nSample data generation complete!")
    print(f"Files saved to: {output_path.absolute()}")
    
    return {
        "users": user_profiles,
        "products": products_df,
        "stores": stores_df,
        "transactions": transactions_df,
        "labels": labels_df,
    }


# Example usage
if __name__ == "__main__":
    data = generate_sample_data(
        output_dir="data",
        n_users=100,
        n_products=50,
        n_stores=10,
        n_transactions=1000,
    )
    
    print("\nData Summary:")
    print(f"  Users: {len(data['users'])}")
    print(f"  Products: {len(data['products'])}")
    print(f"  Stores: {len(data['stores'])}")
    print(f"  Transactions: {len(data['transactions'])}")
    print(f"  Training Labels: {len(data['labels'])}")
