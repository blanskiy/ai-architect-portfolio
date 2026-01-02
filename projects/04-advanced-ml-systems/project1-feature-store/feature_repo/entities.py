"""
Entity Definitions
Entities are the primary keys for feature lookup.

An entity represents a real-world object (user, product, store)
that features are associated with.
"""

from feast import Entity

# =============================================================================
# USER ENTITY
# =============================================================================
# Represents a customer in the system
# Features keyed by user_id include purchase history, preferences, etc.

user = Entity(
    name="user_id",
    description="Unique identifier for a customer",
    # join_keys is inferred from name, but can be explicit:
    # join_keys=["user_id"],
)


# =============================================================================
# PRODUCT ENTITY
# =============================================================================
# Represents a product (e.g., STIHL chainsaw, trimmer)
# Features keyed by product_id include ratings, inventory, popularity

product = Entity(
    name="product_id",
    description="Unique identifier for a product (SKU)",
)


# =============================================================================
# STORE ENTITY
# =============================================================================
# Represents a physical or online store/dealer
# Features keyed by store_id include location data, sales volume

store = Entity(
    name="store_id",
    description="Unique identifier for a store or dealer",
)


# =============================================================================
# COMPOSITE ENTITY EXAMPLE
# =============================================================================
# For user-product interactions (e.g., user's history with specific product)
# This would require a feature view with multiple entities

user_product = Entity(
    name="user_product",
    description="User-product interaction entity",
    join_keys=["user_id", "product_id"],
)
