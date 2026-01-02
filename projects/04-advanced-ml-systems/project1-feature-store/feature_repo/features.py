"""
Feature View Definitions
Feature views define logical groupings of features and their schemas.

A feature view specifies:
- Which entity the features belong to
- The schema (feature names and types)
- The data source
- TTL (time-to-live) for online store
- Whether to enable online serving
"""

from datetime import timedelta
from feast import FeatureView, Field, FeatureService
from feast.types import Float32, Float64, Int64, String, Bool
from feast.on_demand_feature_view import on_demand_feature_view
import pandas as pd

from entities import user, product, store
from data_sources import (
    user_transactions_source,
    user_profile_source,
    product_source,
    product_stats_source,
    store_source,
)


# =============================================================================
# USER TRANSACTION FEATURES
# =============================================================================
# Aggregated features from user purchase history

user_transaction_features = FeatureView(
    name="user_transaction_features",
    description="User purchase behavior features computed from transaction history",
    entities=[user],
    ttl=timedelta(days=1),  # Features expire after 1 day in online store
    schema=[
        # Purchase aggregations (30-day window)
        Field(name="avg_purchase_amount_30d", dtype=Float32, description="Average purchase amount in last 30 days"),
        Field(name="total_purchase_amount_30d", dtype=Float32, description="Total purchase amount in last 30 days"),
        Field(name="purchase_count_30d", dtype=Int64, description="Number of purchases in last 30 days"),
        Field(name="max_purchase_amount_30d", dtype=Float32, description="Maximum single purchase in last 30 days"),
        
        # Purchase aggregations (90-day window)
        Field(name="avg_purchase_amount_90d", dtype=Float32, description="Average purchase amount in last 90 days"),
        Field(name="purchase_count_90d", dtype=Int64, description="Number of purchases in last 90 days"),
        
        # Lifetime aggregations
        Field(name="lifetime_purchase_count", dtype=Int64, description="Total purchases ever"),
        Field(name="lifetime_purchase_amount", dtype=Float32, description="Total amount ever spent"),
        
        # Recency features
        Field(name="days_since_last_purchase", dtype=Int64, description="Days since most recent purchase"),
        Field(name="days_since_first_purchase", dtype=Int64, description="Days since first purchase (tenure)"),
    ],
    source=user_transactions_source,
    online=True,  # Enable online serving
    tags={"team": "ml", "domain": "user"},
)


# =============================================================================
# USER PROFILE FEATURES
# =============================================================================
# Static/slow-changing user attributes

user_profile_features = FeatureView(
    name="user_profile_features",
    description="User demographic and profile features",
    entities=[user],
    ttl=timedelta(days=7),  # Profile features change less frequently
    schema=[
        Field(name="account_age_days", dtype=Int64, description="Days since account creation"),
        Field(name="is_premium_member", dtype=Bool, description="Whether user is premium member"),
        Field(name="preferred_category", dtype=String, description="User's most purchased category"),
        Field(name="home_store_id", dtype=String, description="User's preferred store"),
        Field(name="email_opt_in", dtype=Bool, description="Email marketing opt-in status"),
    ],
    source=user_profile_source,
    online=True,
    tags={"team": "ml", "domain": "user"},
)


# =============================================================================
# PRODUCT FEATURES
# =============================================================================
# Product catalog features

product_features = FeatureView(
    name="product_features",
    description="Product catalog and metadata features",
    entities=[product],
    ttl=timedelta(days=1),
    schema=[
        Field(name="product_name", dtype=String, description="Product display name"),
        Field(name="category", dtype=String, description="Product category"),
        Field(name="subcategory", dtype=String, description="Product subcategory"),
        Field(name="price", dtype=Float32, description="Current price"),
        Field(name="cost", dtype=Float32, description="Product cost"),
        Field(name="margin_pct", dtype=Float32, description="Profit margin percentage"),
        Field(name="weight_lbs", dtype=Float32, description="Product weight in pounds"),
        Field(name="is_seasonal", dtype=Bool, description="Whether product is seasonal"),
    ],
    source=product_source,
    online=True,
    tags={"team": "ml", "domain": "product"},
)


# =============================================================================
# PRODUCT STATISTICS FEATURES
# =============================================================================
# Aggregated product popularity and performance metrics

product_stats_features = FeatureView(
    name="product_stats_features",
    description="Product statistics and popularity metrics",
    entities=[product],
    ttl=timedelta(hours=6),  # Stats update more frequently
    schema=[
        Field(name="avg_rating", dtype=Float32, description="Average customer rating"),
        Field(name="rating_count", dtype=Int64, description="Number of ratings"),
        Field(name="view_count_7d", dtype=Int64, description="Product views in last 7 days"),
        Field(name="purchase_count_7d", dtype=Int64, description="Purchases in last 7 days"),
        Field(name="conversion_rate_7d", dtype=Float32, description="View-to-purchase rate"),
        Field(name="return_rate_30d", dtype=Float32, description="Return rate in last 30 days"),
        Field(name="inventory_level", dtype=Int64, description="Current inventory count"),
        Field(name="days_of_inventory", dtype=Int64, description="Days of inventory remaining"),
    ],
    source=product_stats_source,
    online=True,
    tags={"team": "ml", "domain": "product"},
)


# =============================================================================
# STORE FEATURES
# =============================================================================
# Store/dealer features

store_features = FeatureView(
    name="store_features",
    description="Store and dealer features",
    entities=[store],
    ttl=timedelta(days=1),
    schema=[
        Field(name="store_name", dtype=String, description="Store display name"),
        Field(name="store_type", dtype=String, description="Store type (dealer, retail, online)"),
        Field(name="region", dtype=String, description="Geographic region"),
        Field(name="state", dtype=String, description="State"),
        Field(name="avg_transaction_value", dtype=Float32, description="Average transaction value"),
        Field(name="monthly_sales_volume", dtype=Float32, description="Monthly sales volume"),
        Field(name="customer_count", dtype=Int64, description="Number of unique customers"),
    ],
    source=store_source,
    online=True,
    tags={"team": "ml", "domain": "store"},
)


# =============================================================================
# ON-DEMAND FEATURE VIEW
# =============================================================================
# Features computed at request time (not materialized)
# Useful for features that depend on request context

@on_demand_feature_view(
    sources=[user_transaction_features, user_profile_features],
    schema=[
        Field(name="purchase_velocity", dtype=Float32, description="Purchases per month since first purchase"),
        Field(name="is_high_value_customer", dtype=Bool, description="Whether customer is high value"),
        Field(name="engagement_score", dtype=Float32, description="Composite engagement score"),
    ],
)
def user_derived_features(inputs: pd.DataFrame) -> pd.DataFrame:
    """Compute derived features at request time."""
    
    df = pd.DataFrame()
    
    # Purchase velocity: purchases per month since first purchase
    months_active = inputs["days_since_first_purchase"] / 30.0
    df["purchase_velocity"] = inputs["lifetime_purchase_count"] / months_active.clip(lower=1)
    
    # High value customer: >$1000 lifetime spend or >10 purchases
    df["is_high_value_customer"] = (
        (inputs["lifetime_purchase_amount"] > 1000) | 
        (inputs["lifetime_purchase_count"] > 10)
    )
    
    # Engagement score: weighted combination
    recency_score = 1.0 / (1 + inputs["days_since_last_purchase"] / 30.0)
    frequency_score = inputs["purchase_count_30d"] / 5.0  # Normalize
    monetary_score = inputs["avg_purchase_amount_30d"] / 200.0  # Normalize
    
    df["engagement_score"] = (
        0.3 * recency_score + 
        0.3 * frequency_score + 
        0.4 * monetary_score
    ).clip(0, 1)
    
    return df


# =============================================================================
# FEATURE SERVICES
# =============================================================================
# Group features for specific use cases

# For purchase prediction model
purchase_prediction_service = FeatureService(
    name="purchase_prediction",
    description="Features for predicting next purchase",
    features=[
        user_transaction_features,
        user_profile_features,
        user_derived_features,
    ],
    tags={"model": "purchase_prediction"},
)

# For product recommendation model
recommendation_service = FeatureService(
    name="product_recommendation",
    description="Features for product recommendations",
    features=[
        user_transaction_features[["avg_purchase_amount_30d", "preferred_category"]],
        product_features,
        product_stats_features[["avg_rating", "purchase_count_7d"]],
    ],
    tags={"model": "recommendations"},
)

# For store analytics
store_analytics_service = FeatureService(
    name="store_analytics",
    description="Features for store performance analysis",
    features=[
        store_features,
    ],
    tags={"domain": "analytics"},
)
