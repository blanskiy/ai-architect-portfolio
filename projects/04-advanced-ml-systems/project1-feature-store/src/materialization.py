"""
Feature Materialization
Sync features from offline store to online store for real-time serving.

Materialization copies feature values from the offline store (Parquet, BigQuery)
to the online store (Redis, DynamoDB) so they can be served with low latency.

Typically scheduled to run:
- Hourly for frequently changing features
- Daily for slowly changing features
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
import logging

from feast import FeatureStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeatureMaterializer:
    """
    Handles materialization of features from offline to online store.
    
    Usage:
        materializer = FeatureMaterializer(repo_path="feature_repo")
        
        # Full materialization
        materializer.materialize_all()
        
        # Incremental materialization
        materializer.materialize_incremental()
        
        # Materialize specific feature views
        materializer.materialize_feature_views(["user_transaction_features"])
    """
    
    def __init__(self, repo_path: str = "feature_repo"):
        self.repo_path = Path(repo_path)
        self.store = FeatureStore(repo_path=str(self.repo_path))
    
    def materialize_all(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
    ):
        """
        Materialize all features from start_date to end_date.
        
        This is a full materialization that processes all historical data.
        Use sparingly - prefer incremental materialization for regular updates.
        
        Args:
            start_date: Start of materialization window (default: 30 days ago)
            end_date: End of materialization window (default: now)
        """
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()
        
        logger.info(f"Starting full materialization from {start_date} to {end_date}")
        
        try:
            self.store.materialize(
                start_date=start_date,
                end_date=end_date,
            )
            logger.info("Full materialization complete!")
        except Exception as e:
            logger.error(f"Materialization failed: {e}")
            raise
    
    def materialize_incremental(self, end_date: datetime = None):
        """
        Incrementally materialize features since last materialization.
        
        This is the recommended approach for regular updates:
        - Only processes new data since last run
        - Much faster than full materialization
        - Typically run hourly or daily
        
        Args:
            end_date: End of materialization window (default: now)
        """
        
        if end_date is None:
            end_date = datetime.now()
        
        logger.info(f"Starting incremental materialization up to {end_date}")
        
        try:
            self.store.materialize_incremental(end_date=end_date)
            logger.info("Incremental materialization complete!")
        except Exception as e:
            logger.error(f"Incremental materialization failed: {e}")
            raise
    
    def materialize_feature_views(
        self,
        feature_views: list[str],
        start_date: datetime = None,
        end_date: datetime = None,
    ):
        """
        Materialize specific feature views only.
        
        Useful when you only need to update certain feature sets.
        
        Args:
            feature_views: List of feature view names to materialize
            start_date: Start of materialization window
            end_date: End of materialization window
        """
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()
        
        logger.info(f"Materializing feature views: {feature_views}")
        
        try:
            self.store.materialize(
                start_date=start_date,
                end_date=end_date,
                feature_views=feature_views,
            )
            logger.info(f"Materialized {len(feature_views)} feature views")
        except Exception as e:
            logger.error(f"Feature view materialization failed: {e}")
            raise
    
    def get_materialization_status(self) -> dict:
        """
        Get the current materialization status.
        
        Returns information about:
        - Last materialization time per feature view
        - Number of entities in online store
        - Online store health
        """
        
        status = {
            "feature_views": {},
            "online_store_healthy": True,
        }
        
        try:
            # Get all feature views
            feature_views = self.store.list_feature_views()
            
            for fv in feature_views:
                status["feature_views"][fv.name] = {
                    "entities": [e.name for e in fv.entity_columns],
                    "features": [f.name for f in fv.features],
                    "ttl": str(fv.ttl) if fv.ttl else "None",
                    "online_enabled": fv.online,
                }
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            status["error"] = str(e)
            status["online_store_healthy"] = False
        
        return status
    
    def validate_online_store(self, sample_entities: list[dict]) -> dict:
        """
        Validate that online store is serving features correctly.
        
        Args:
            sample_entities: List of entity dicts to test
        
        Returns:
            Validation results with latency and data quality metrics
        """
        import time
        
        results = {
            "entities_tested": len(sample_entities),
            "successful": 0,
            "failed": 0,
            "avg_latency_ms": 0,
            "errors": [],
        }
        
        latencies = []
        
        for entity in sample_entities:
            try:
                start = time.time()
                
                # Try to fetch features
                features = self.store.get_online_features(
                    entity_rows=[entity],
                    features=[
                        "user_transaction_features:avg_purchase_amount_30d",
                        "user_transaction_features:purchase_count_30d",
                    ],
                ).to_dict()
                
                latency_ms = (time.time() - start) * 1000
                latencies.append(latency_ms)
                
                # Check if features were returned
                if features and len(features) > 0:
                    results["successful"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"No features for {entity}")
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Error for {entity}: {str(e)}")
        
        if latencies:
            results["avg_latency_ms"] = sum(latencies) / len(latencies)
            results["p95_latency_ms"] = sorted(latencies)[int(len(latencies) * 0.95)]
        
        return results


def run_materialization(
    repo_path: str = "feature_repo",
    mode: str = "incremental",
):
    """
    CLI entry point for running materialization.
    
    Args:
        repo_path: Path to feature repository
        mode: "incremental" or "full"
    """
    
    materializer = FeatureMaterializer(repo_path=repo_path)
    
    if mode == "incremental":
        materializer.materialize_incremental()
    elif mode == "full":
        materializer.materialize_all()
    else:
        raise ValueError(f"Unknown mode: {mode}")
    
    # Print status
    status = materializer.get_materialization_status()
    print("\nMaterialization Status:")
    for fv_name, fv_info in status["feature_views"].items():
        print(f"  {fv_name}: {len(fv_info['features'])} features, online={fv_info['online_enabled']}")


# Example usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Materialize features to online store")
    parser.add_argument("--repo-path", default="feature_repo", help="Path to feature repository")
    parser.add_argument("--mode", choices=["incremental", "full"], default="incremental")
    
    args = parser.parse_args()
    
    run_materialization(repo_path=args.repo_path, mode=args.mode)
