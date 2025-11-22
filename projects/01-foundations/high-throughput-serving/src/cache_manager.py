#!/usr/bin/env python3
"""
Redis cache manager for ML predictions.

Caches prediction results to avoid redundant model inference.
Cache key: hash of image content
Cache value: prediction results (JSON)
TTL: 1 hour (configurable)
"""

import redis
import hashlib
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching of ML predictions using Redis."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        ttl: int = 3600,
        enabled: bool = True
    ):
        """Initialize cache manager."""
        self.ttl = ttl
        self.enabled = enabled
        self.redis_client = None
        self.cache_hits = 0
        self.cache_misses = 0
        
        if not enabled:
            logger.info("Cache disabled")
            return
        
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_connect_timeout=5
            )
            self.redis_client.ping()
            logger.info(f"Redis connected: {host}:{port}")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Cache disabled.")
            self.enabled = False
            self.redis_client = None
    
    def _generate_key(self, image_data: bytes) -> str:
        """Generate cache key from image data."""
        hash_obj = hashlib.sha256(image_data)
        return f"prediction:{hash_obj.hexdigest()}"
    
    def get(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """Get cached prediction for image."""
        if not self.enabled or not self.redis_client:
            return None
        
        try:
            key = self._generate_key(image_data)
            cached_value = self.redis_client.get(key)
            
            if cached_value:
                self.cache_hits += 1
                logger.info(f"Cache HIT", extra={'cache_key': key[:16] + '...'})
                return json.loads(cached_value)
            else:
                self.cache_misses += 1
                logger.debug(f"Cache MISS", extra={'cache_key': key[:16] + '...'})
                return None
                
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, image_data: bytes, prediction_result: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Cache prediction result."""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            key = self._generate_key(image_data)
            value = json.dumps(prediction_result)
            ttl_seconds = ttl or self.ttl
            
            self.redis_client.setex(name=key, time=ttl_seconds, value=value)
            logger.debug(f"Cache SET", extra={'cache_key': key[:16] + '...'})
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def clear_all(self) -> bool:
        """Clear all cached predictions."""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            keys = self.redis_client.keys("prediction:*")
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Cache cleared: {len(keys)} keys deleted")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            'enabled': self.enabled,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': self.get_hit_rate(),
            'total_requests': self.cache_hits + self.cache_misses
        }
        
        if self.enabled and self.redis_client:
            try:
                info = self.redis_client.info('stats')
                stats.update({
                    'redis_connected': True,
                    'redis_keys': self.redis_client.dbsize(),
                    'redis_memory_used': info.get('used_memory_human', 'N/A')
                })
            except Exception:
                stats['redis_connected'] = False
        else:
            stats['redis_connected'] = False
        
        return stats
    
    def get_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return round((self.cache_hits / total) * 100, 2)
    
    def is_healthy(self) -> bool:
        """Check if cache is healthy."""
        if not self.enabled or not self.redis_client:
            return False
        try:
            return self.redis_client.ping()
        except Exception:
            return False
