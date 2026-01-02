"""
Training Data Retrieval
Get historical features for model training with point-in-time correctness.

The key concept here is POINT-IN-TIME JOINS:
- When creating training data, we need features AS OF the label event time
- This prevents data leakage (using future information to predict past events)

Example:
    If a user made a purchase on Jan 15th:
    - We use features computed BEFORE Jan 15th
    - We do NOT use features computed AFTER Jan 15th (that would be leakage!)
"""

import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union
import logging

from feast import FeatureStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrainingDataBuilder:
    """
    Builds training datasets with point-in-time correct features.
    
    Usage:
        builder = TrainingDataBuilder(repo_path="feature_repo")
        
        # Create entity dataframe with labels
        entity_df = pd.DataFrame({
            "user_id": ["user_1", "user_2", "user_3"],
            "event_timestamp": [datetime(2024, 1, 15), datetime(2024, 1, 16), datetime(2024, 1, 17)],
            "label": [1, 0, 1]  # Did they purchase?
        })
        
        # Get training features
        training_df = builder.get_training_features(
            entity_df=entity_df,
            features=["user_transaction_features:avg_purchase_amount_30d"]
        )
    """
    
    def __init__(self, repo_path: str = "feature_repo"):
        self.repo_path = Path(repo_path)
        self.store = FeatureStore(repo_path=str(self.repo_path))
    
    def get_training_features(
        self,
        entity_df: pd.DataFrame,
        features: list[str],
        full_feature_names: bool = True,
    ) -> pd.DataFrame:
        """
        Get historical features for training with point-in-time correctness.
        
        Args:
            entity_df: DataFrame with entity keys and event_timestamp
                Required columns:
                - Entity key columns (e.g., user_id, product_id)
                - event_timestamp: The timestamp for point-in-time lookup
                Optional columns:
                - label: Training label
                - Any other columns to keep
            
            features: List of feature references in format:
                "feature_view_name:feature_name"
                or
                "feature_service_name"
            
            full_feature_names: If True, prefix column names with feature view
        
        Returns:
            DataFrame with entity keys, timestamps, and features joined
        
        Example:
            features = [
                "user_transaction_features:avg_purchase_amount_30d",
                "user_transaction_features:purchase_count_30d",
                "user_profile_features:is_premium_member",
            ]
        """
        
        logger.info(f"Retrieving {len(features)} features for {len(entity_df)} entities")
        
        # Ensure event_timestamp is datetime
        entity_df = entity_df.copy()
        entity_df['event_timestamp'] = pd.to_datetime(entity_df['event_timestamp'])
        
        try:
            # Get historical features (point-in-time join)
            training_data = self.store.get_historical_features(
                entity_df=entity_df,
                features=features,
                full_feature_names=full_feature_names,
            )
            
            # Convert to DataFrame
            result_df = training_data.to_df()
            
            logger.info(f"Retrieved {len(result_df)} rows with {len(result_df.columns)} columns")
            
            return result_df
            
        except Exception as e:
            logger.error(f"Error retrieving training features: {e}")
            raise
    
    def get_training_features_from_service(
        self,
        entity_df: pd.DataFrame,
        feature_service: str,
    ) -> pd.DataFrame:
        """
        Get features using a predefined feature service.
        
        Feature services group related features for a specific use case.
        
        Args:
            entity_df: DataFrame with entity keys and event_timestamp
            feature_service: Name of the feature service
        
        Returns:
            DataFrame with all features from the service
        """
        
        logger.info(f"Retrieving features from service: {feature_service}")
        
        entity_df = entity_df.copy()
        entity_df['event_timestamp'] = pd.to_datetime(entity_df['event_timestamp'])
        
        try:
            training_data = self.store.get_historical_features(
                entity_df=entity_df,
                features=self.store.get_feature_service(feature_service),
            )
            
            return training_data.to_df()
            
        except Exception as e:
            logger.error(f"Error retrieving from feature service: {e}")
            raise
    
    def create_entity_df_for_date_range(
        self,
        entity_source_df: pd.DataFrame,
        entity_column: str,
        start_date: datetime,
        end_date: datetime,
        frequency: str = "D",
    ) -> pd.DataFrame:
        """
        Create an entity DataFrame with timestamps for a date range.
        
        Useful for creating training data where you want features
        at regular intervals for each entity.
        
        Args:
            entity_source_df: Source of entity IDs
            entity_column: Name of entity column
            start_date: Start of date range
            end_date: End of date range
            frequency: Pandas frequency string ("D"=daily, "W"=weekly)
        
        Returns:
            Cross-product of entities and timestamps
        """
        
        # Generate date range
        dates = pd.date_range(start=start_date, end=end_date, freq=frequency)
        
        # Get unique entities
        entities = entity_source_df[entity_column].unique()
        
        # Create cross product
        rows = []
        for entity_id in entities:
            for date in dates:
                rows.append({
                    entity_column: entity_id,
                    "event_timestamp": date,
                })
        
        return pd.DataFrame(rows)
    
    def validate_training_data(self, df: pd.DataFrame) -> dict:
        """
        Validate training data quality.
        
        Checks for:
        - Missing values
        - Infinite values
        - Data type issues
        - Feature distribution anomalies
        
        Returns:
            Validation report
        """
        
        report = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "issues": [],
            "column_stats": {},
        }
        
        for col in df.columns:
            col_stats = {
                "dtype": str(df[col].dtype),
                "missing_count": df[col].isna().sum(),
                "missing_pct": df[col].isna().mean() * 100,
            }
            
            # Check for issues
            if col_stats["missing_pct"] > 10:
                report["issues"].append(f"High missing rate in {col}: {col_stats['missing_pct']:.1f}%")
            
            # Numeric stats
            if pd.api.types.is_numeric_dtype(df[col]):
                col_stats["min"] = df[col].min()
                col_stats["max"] = df[col].max()
                col_stats["mean"] = df[col].mean()
                col_stats["std"] = df[col].std()
                
                # Check for infinites
                inf_count = (~df[col].isna() & ~pd.api.types.is_finite(df[col])).sum() if pd.api.types.is_float_dtype(df[col]) else 0
                if inf_count > 0:
                    report["issues"].append(f"Infinite values in {col}: {inf_count}")
            
            report["column_stats"][col] = col_stats
        
        report["is_valid"] = len(report["issues"]) == 0
        
        return report


def create_training_dataset(
    repo_path: str = "feature_repo",
    labels_path: str = "data/labels.parquet",
    output_path: str = "data/training_data.parquet",
    features: list[str] = None,
):
    """
    End-to-end training dataset creation.
    
    1. Load labels/entities
    2. Retrieve point-in-time features
    3. Validate data quality
    4. Save training dataset
    """
    
    builder = TrainingDataBuilder(repo_path=repo_path)
    
    # Load labels
    logger.info(f"Loading labels from {labels_path}")
    labels_df = pd.read_parquet(labels_path)
    
    # Default features if not specified
    if features is None:
        features = [
            "user_transaction_features:avg_purchase_amount_30d",
            "user_transaction_features:purchase_count_30d",
            "user_transaction_features:days_since_last_purchase",
            "user_transaction_features:lifetime_purchase_amount",
        ]
    
    # Get features
    logger.info("Retrieving historical features...")
    training_df = builder.get_training_features(
        entity_df=labels_df,
        features=features,
    )
    
    # Validate
    logger.info("Validating training data...")
    validation = builder.validate_training_data(training_df)
    
    if not validation["is_valid"]:
        logger.warning("Validation issues found:")
        for issue in validation["issues"]:
            logger.warning(f"  - {issue}")
    
    # Save
    logger.info(f"Saving training data to {output_path}")
    training_df.to_parquet(output_path, index=False)
    
    logger.info(f"Created training dataset: {len(training_df)} rows, {len(training_df.columns)} columns")
    
    return training_df


# Example usage
if __name__ == "__main__":
    # Example: Create training data
    builder = TrainingDataBuilder(repo_path="feature_repo")
    
    # Sample entity dataframe
    entity_df = pd.DataFrame({
        "user_id": ["user_001", "user_002", "user_003", "user_004", "user_005"],
        "event_timestamp": [
            datetime(2024, 1, 15, 10, 0),
            datetime(2024, 1, 16, 14, 30),
            datetime(2024, 1, 17, 9, 0),
            datetime(2024, 1, 18, 16, 45),
            datetime(2024, 1, 19, 11, 15),
        ],
        "label": [1, 0, 1, 0, 1],  # Did they make a high-value purchase?
    })
    
    print("Entity DataFrame:")
    print(entity_df)
    print()
    
    # This would normally call the feature store
    # training_df = builder.get_training_features(
    #     entity_df=entity_df,
    #     features=[
    #         "user_transaction_features:avg_purchase_amount_30d",
    #         "user_transaction_features:purchase_count_30d",
    #     ]
    # )
    # print("Training DataFrame:")
    # print(training_df)
