"""
Online Feature Serving
Real-time feature retrieval for model inference.

This module provides low-latency feature lookup from the online store (Redis).
Features are pre-computed and materialized, so serving is a simple key-value lookup.

Typical latency: 1-10ms per request
"""

import time
import logging
from typing import Optional, Union
from dataclasses import dataclass
from pathlib import Path

from feast import FeatureStore
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FeatureResponse:
    """Response from online feature serving."""
    features: dict
    entity_key: dict
    latency_ms: float
    success: bool
    error: Optional[str] = None


class OnlineFeatureServer:
    """
    Serves features in real-time from the online store.
    
    Usage:
        server = OnlineFeatureServer(repo_path="feature_repo")
        
        # Get features for a single user
        response = server.get_user_features(user_id="user_123")
        
        # Get features for multiple users (batch)
        responses = server.get_user_features_batch(
            user_ids=["user_1", "user_2", "user_3"]
        )
        
        # Get features with custom feature list
        response = server.get_features(
            entity_rows=[{"user_id": "user_123"}],
            features=["user_transaction_features:avg_purchase_amount_30d"]
        )
    """
    
    def __init__(self, repo_path: str = "feature_repo"):
        self.repo_path = Path(repo_path)
        self.store = FeatureStore(repo_path=str(self.repo_path))
        
        # Default feature sets for common use cases
        self.user_features = [
            "user_transaction_features:avg_purchase_amount_30d",
            "user_transaction_features:purchase_count_30d",
            "user_transaction_features:days_since_last_purchase",
            "user_transaction_features:lifetime_purchase_amount",
            "user_transaction_features:lifetime_purchase_count",
        ]
        
        self.product_features = [
            "product_features:price",
            "product_features:category",
            "product_stats_features:avg_rating",
            "product_stats_features:purchase_count_7d",
        ]
    
    def get_features(
        self,
        entity_rows: list[dict],
        features: list[str],
    ) -> list[FeatureResponse]:
        """
        Get online features for arbitrary entities.
        
        Args:
            entity_rows: List of entity key dicts
                Example: [{"user_id": "user_123"}, {"user_id": "user_456"}]
            features: List of feature references
                Example: ["user_features:avg_purchase_30d"]
        
        Returns:
            List of FeatureResponse objects
        """
        
        start_time = time.time()
        
        try:
            # Call Feast online store
            online_response = self.store.get_online_features(
                entity_rows=entity_rows,
                features=features,
            )
            
            # Convert to dict
            feature_dict = online_response.to_dict()
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Build response for each entity
            responses = []
            num_entities = len(entity_rows)
            
            for i in range(num_entities):
                entity_features = {}
                for key, values in feature_dict.items():
                    if key not in entity_rows[i]:  # Skip entity keys
                        entity_features[key] = values[i]
                
                responses.append(FeatureResponse(
                    features=entity_features,
                    entity_key=entity_rows[i],
                    latency_ms=latency_ms / num_entities,  # Approximate per-entity
                    success=True,
                ))
            
            logger.debug(f"Retrieved features for {num_entities} entities in {latency_ms:.2f}ms")
            
            return responses
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Error getting online features: {e}")
            
            return [
                FeatureResponse(
                    features={},
                    entity_key=entity,
                    latency_ms=latency_ms,
                    success=False,
                    error=str(e),
                )
                for entity in entity_rows
            ]
    
    def get_user_features(
        self,
        user_id: str,
        features: list[str] = None,
    ) -> FeatureResponse:
        """
        Get features for a single user.
        
        Args:
            user_id: User identifier
            features: Optional custom feature list (default: self.user_features)
        
        Returns:
            FeatureResponse with user features
        """
        
        if features is None:
            features = self.user_features
        
        responses = self.get_features(
            entity_rows=[{"user_id": user_id}],
            features=features,
        )
        
        return responses[0]
    
    def get_user_features_batch(
        self,
        user_ids: list[str],
        features: list[str] = None,
    ) -> list[FeatureResponse]:
        """
        Get features for multiple users in one call.
        
        More efficient than calling get_user_features multiple times.
        
        Args:
            user_ids: List of user identifiers
            features: Optional custom feature list
        
        Returns:
            List of FeatureResponse objects
        """
        
        if features is None:
            features = self.user_features
        
        entity_rows = [{"user_id": uid} for uid in user_ids]
        
        return self.get_features(
            entity_rows=entity_rows,
            features=features,
        )
    
    def get_product_features(
        self,
        product_id: str,
        features: list[str] = None,
    ) -> FeatureResponse:
        """
        Get features for a single product.
        
        Args:
            product_id: Product identifier
            features: Optional custom feature list
        
        Returns:
            FeatureResponse with product features
        """
        
        if features is None:
            features = self.product_features
        
        responses = self.get_features(
            entity_rows=[{"product_id": product_id}],
            features=features,
        )
        
        return responses[0]
    
    def get_recommendation_features(
        self,
        user_id: str,
        product_ids: list[str],
    ) -> dict:
        """
        Get features for recommendation model.
        
        Combines user features with features for candidate products.
        
        Args:
            user_id: User to get recommendations for
            product_ids: List of candidate product IDs
        
        Returns:
            Dict with user features and product features for each candidate
        """
        
        start_time = time.time()
        
        # Get user features
        user_response = self.get_user_features(user_id)
        
        # Get product features for all candidates
        product_entity_rows = [{"product_id": pid} for pid in product_ids]
        product_responses = self.get_features(
            entity_rows=product_entity_rows,
            features=self.product_features,
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "user_id": user_id,
            "user_features": user_response.features,
            "candidates": [
                {
                    "product_id": product_ids[i],
                    "features": product_responses[i].features,
                }
                for i in range(len(product_ids))
            ],
            "total_latency_ms": latency_ms,
        }
    
    def health_check(self) -> dict:
        """
        Check health of the online store.
        
        Returns:
            Health status dict
        """
        
        try:
            start = time.time()
            
            # Try to fetch a dummy feature
            self.store.get_online_features(
                entity_rows=[{"user_id": "health_check_user"}],
                features=["user_transaction_features:avg_purchase_amount_30d"],
            )
            
            latency_ms = (time.time() - start) * 1000
            
            return {
                "healthy": True,
                "latency_ms": latency_ms,
                "message": "Online store is responding",
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "latency_ms": None,
                "message": f"Online store error: {str(e)}",
            }


class FeatureServerWithCache:
    """
    Feature server with local caching for frequently accessed entities.
    
    Adds a local cache layer to reduce calls to the online store.
    Useful for hot entities (popular users/products).
    """
    
    def __init__(
        self,
        repo_path: str = "feature_repo",
        cache_ttl_seconds: int = 60,
        max_cache_size: int = 10000,
    ):
        self.server = OnlineFeatureServer(repo_path=repo_path)
        self.cache_ttl = cache_ttl_seconds
        self.max_cache_size = max_cache_size
        
        # Simple dict cache (use Redis in production)
        self._cache: dict[str, tuple[dict, float]] = {}
    
    def _get_cache_key(self, entity: dict, features: list[str]) -> str:
        """Generate cache key from entity and features."""
        entity_str = "_".join(f"{k}={v}" for k, v in sorted(entity.items()))
        features_str = "_".join(sorted(features))
        return f"{entity_str}|{features_str}"
    
    def get_features(
        self,
        entity_rows: list[dict],
        features: list[str],
    ) -> list[FeatureResponse]:
        """Get features with caching."""
        
        responses = []
        uncached_entities = []
        uncached_indices = []
        
        current_time = time.time()
        
        # Check cache for each entity
        for i, entity in enumerate(entity_rows):
            cache_key = self._get_cache_key(entity, features)
            
            if cache_key in self._cache:
                cached_data, cached_time = self._cache[cache_key]
                
                # Check TTL
                if current_time - cached_time < self.cache_ttl:
                    responses.append(FeatureResponse(
                        features=cached_data,
                        entity_key=entity,
                        latency_ms=0.1,  # Cache hit
                        success=True,
                    ))
                    continue
            
            # Cache miss
            uncached_entities.append(entity)
            uncached_indices.append(i)
            responses.append(None)  # Placeholder
        
        # Fetch uncached entities from online store
        if uncached_entities:
            online_responses = self.server.get_features(
                entity_rows=uncached_entities,
                features=features,
            )
            
            # Update cache and responses
            for j, response in enumerate(online_responses):
                idx = uncached_indices[j]
                responses[idx] = response
                
                # Cache successful responses
                if response.success:
                    cache_key = self._get_cache_key(uncached_entities[j], features)
                    self._cache[cache_key] = (response.features, current_time)
            
            # Evict old entries if cache is full
            if len(self._cache) > self.max_cache_size:
                self._evict_oldest()
        
        return responses
    
    def _evict_oldest(self):
        """Evict oldest cache entries."""
        sorted_keys = sorted(
            self._cache.keys(),
            key=lambda k: self._cache[k][1]
        )
        
        # Remove oldest 10%
        num_to_remove = len(sorted_keys) // 10
        for key in sorted_keys[:num_to_remove]:
            del self._cache[key]


# Example usage
if __name__ == "__main__":
    server = OnlineFeatureServer(repo_path="feature_repo")
    
    # Health check
    print("Health check:")
    print(server.health_check())
    print()
    
    # This would work with a running feature store:
    # # Get user features
    # response = server.get_user_features(user_id="user_123")
    # print(f"User features: {response.features}")
    # print(f"Latency: {response.latency_ms:.2f}ms")
    # 
    # # Batch request
    # responses = server.get_user_features_batch(
    #     user_ids=["user_1", "user_2", "user_3"]
    # )
    # for r in responses:
    #     print(f"  {r.entity_key}: {r.features}")
