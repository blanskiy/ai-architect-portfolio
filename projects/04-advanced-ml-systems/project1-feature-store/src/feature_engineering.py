"""
Feature Engineering
Compute features from raw data sources.

This module contains the logic for computing features that will be stored
in the feature store. Features are computed in batch and written to the
offline store (Parquet files).

In production, this would typically be:
- Spark jobs for large-scale processing
- dbt transformations
- Airflow DAGs for scheduling
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class FeatureEngineer:
    """
    Computes features from raw transaction data.
    
    Usage:
        engineer = FeatureEngineer()
        
        # Compute user features
        user_features = engineer.compute_user_transaction_features(
            transactions_df=transactions,
            as_of_date=datetime.now()
        )
        
        # Save to offline store
        user_features.to_parquet("data/user_transactions.parquet")
    """
    
    def __init__(self, output_dir: str = "data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def compute_user_transaction_features(
        self,
        transactions_df: pd.DataFrame,
        as_of_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Compute user transaction features.
        
        Args:
            transactions_df: Raw transactions with columns:
                - user_id: User identifier
                - transaction_date: Transaction timestamp
                - amount: Transaction amount
            as_of_date: Compute features as of this date (default: now)
        
        Returns:
            DataFrame with user_id and computed features
        """
        
        if as_of_date is None:
            as_of_date = datetime.now()
        
        df = transactions_df.copy()
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        
        # Filter to transactions before as_of_date
        df = df[df['transaction_date'] <= as_of_date]
        
        # Calculate days ago for each transaction
        df['days_ago'] = (as_of_date - df['transaction_date']).dt.days
        
        # Group by user
        features = []
        
        for user_id, user_df in df.groupby('user_id'):
            # 30-day window features
            df_30d = user_df[user_df['days_ago'] <= 30]
            # 90-day window features
            df_90d = user_df[user_df['days_ago'] <= 90]
            
            feature_row = {
                'user_id': user_id,
                'event_timestamp': as_of_date,
                'created_timestamp': datetime.now(),
                
                # 30-day aggregations
                'avg_purchase_amount_30d': df_30d['amount'].mean() if len(df_30d) > 0 else 0.0,
                'total_purchase_amount_30d': df_30d['amount'].sum() if len(df_30d) > 0 else 0.0,
                'purchase_count_30d': len(df_30d),
                'max_purchase_amount_30d': df_30d['amount'].max() if len(df_30d) > 0 else 0.0,
                
                # 90-day aggregations
                'avg_purchase_amount_90d': df_90d['amount'].mean() if len(df_90d) > 0 else 0.0,
                'purchase_count_90d': len(df_90d),
                
                # Lifetime aggregations
                'lifetime_purchase_count': len(user_df),
                'lifetime_purchase_amount': user_df['amount'].sum(),
                
                # Recency features
                'days_since_last_purchase': user_df['days_ago'].min(),
                'days_since_first_purchase': user_df['days_ago'].max(),
            }
            features.append(feature_row)
        
        result_df = pd.DataFrame(features)
        
        # Ensure correct types
        result_df = self._cast_types(result_df, {
            'avg_purchase_amount_30d': 'float32',
            'total_purchase_amount_30d': 'float32',
            'purchase_count_30d': 'int64',
            'max_purchase_amount_30d': 'float32',
            'avg_purchase_amount_90d': 'float32',
            'purchase_count_90d': 'int64',
            'lifetime_purchase_count': 'int64',
            'lifetime_purchase_amount': 'float32',
            'days_since_last_purchase': 'int64',
            'days_since_first_purchase': 'int64',
        })
        
        return result_df
    
    def compute_product_stats_features(
        self,
        transactions_df: pd.DataFrame,
        ratings_df: pd.DataFrame,
        views_df: pd.DataFrame,
        inventory_df: pd.DataFrame,
        as_of_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Compute product statistics features.
        
        Args:
            transactions_df: Transaction data
            ratings_df: Product ratings
            views_df: Product view events
            inventory_df: Current inventory levels
            as_of_date: Compute as of this date
        
        Returns:
            DataFrame with product_id and computed features
        """
        
        if as_of_date is None:
            as_of_date = datetime.now()
        
        # Convert dates
        transactions_df = transactions_df.copy()
        transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date'])
        
        views_df = views_df.copy()
        views_df['view_date'] = pd.to_datetime(views_df['view_date'])
        
        features = []
        
        # Get all products
        all_products = set(transactions_df['product_id'].unique()) | set(views_df['product_id'].unique())
        
        for product_id in all_products:
            # 7-day windows
            cutoff_7d = as_of_date - timedelta(days=7)
            cutoff_30d = as_of_date - timedelta(days=30)
            
            # Transaction stats
            product_txns = transactions_df[transactions_df['product_id'] == product_id]
            txns_7d = product_txns[product_txns['transaction_date'] >= cutoff_7d]
            txns_30d = product_txns[product_txns['transaction_date'] >= cutoff_30d]
            
            # View stats
            product_views = views_df[views_df['product_id'] == product_id]
            views_7d = product_views[product_views['view_date'] >= cutoff_7d]
            
            # Rating stats
            product_ratings = ratings_df[ratings_df['product_id'] == product_id] if 'product_id' in ratings_df.columns else pd.DataFrame()
            
            # Inventory
            product_inv = inventory_df[inventory_df['product_id'] == product_id] if 'product_id' in inventory_df.columns else pd.DataFrame()
            
            # Calculate metrics
            view_count_7d = len(views_7d)
            purchase_count_7d = len(txns_7d)
            
            feature_row = {
                'product_id': product_id,
                'event_timestamp': as_of_date,
                'created_timestamp': datetime.now(),
                
                'avg_rating': product_ratings['rating'].mean() if len(product_ratings) > 0 else 0.0,
                'rating_count': len(product_ratings),
                'view_count_7d': view_count_7d,
                'purchase_count_7d': purchase_count_7d,
                'conversion_rate_7d': purchase_count_7d / max(view_count_7d, 1),
                'return_rate_30d': 0.0,  # Would need return data
                'inventory_level': product_inv['quantity'].iloc[0] if len(product_inv) > 0 else 0,
                'days_of_inventory': 30,  # Would calculate from sales velocity
            }
            features.append(feature_row)
        
        result_df = pd.DataFrame(features)
        
        result_df = self._cast_types(result_df, {
            'avg_rating': 'float32',
            'rating_count': 'int64',
            'view_count_7d': 'int64',
            'purchase_count_7d': 'int64',
            'conversion_rate_7d': 'float32',
            'return_rate_30d': 'float32',
            'inventory_level': 'int64',
            'days_of_inventory': 'int64',
        })
        
        return result_df
    
    def _cast_types(self, df: pd.DataFrame, type_map: dict) -> pd.DataFrame:
        """Cast columns to specified types."""
        for col, dtype in type_map.items():
            if col in df.columns:
                df[col] = df[col].fillna(0).astype(dtype)
        return df
    
    def save_features(self, df: pd.DataFrame, name: str):
        """Save features to parquet file."""
        output_path = self.output_dir / f"{name}.parquet"
        df.to_parquet(output_path, index=False)
        print(f"Saved {len(df)} rows to {output_path}")


def compute_all_features(
    transactions_path: str,
    output_dir: str = "data",
    as_of_date: Optional[datetime] = None,
):
    """
    Compute all features from raw data.
    
    This is the main entry point for batch feature computation.
    In production, this would be called by an Airflow DAG or similar.
    """
    
    engineer = FeatureEngineer(output_dir=output_dir)
    
    # Load raw data
    transactions = pd.read_parquet(transactions_path)
    
    # Compute user transaction features
    print("Computing user transaction features...")
    user_features = engineer.compute_user_transaction_features(
        transactions_df=transactions,
        as_of_date=as_of_date,
    )
    engineer.save_features(user_features, "user_transactions")
    
    print("Feature engineering complete!")
    
    return user_features


# Example usage
if __name__ == "__main__":
    # Generate sample data first
    from sample_data import generate_sample_data
    generate_sample_data()
    
    # Compute features
    compute_all_features(
        transactions_path="data/raw_transactions.parquet",
        as_of_date=datetime.now(),
    )
