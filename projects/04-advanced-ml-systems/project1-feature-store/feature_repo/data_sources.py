"""
Data Source Definitions
Define where raw feature data comes from.

Feast supports various data sources:
- FileSource: Parquet files (local or cloud storage)
- BigQuerySource: Google BigQuery tables
- RedshiftSource: AWS Redshift tables
- SnowflakeSource: Snowflake tables
- KafkaSource: Streaming data from Kafka
- PushSource: Features pushed directly via API
"""

from feast import FileSource, PushSource
from feast.data_format import ParquetFormat

# =============================================================================
# USER TRANSACTION DATA SOURCE
# =============================================================================
# Historical transaction data for computing user features
# In production, this would be a BigQuery table or data warehouse

user_transactions_source = FileSource(
    name="user_transactions",
    path="data/user_transactions.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
    description="User transaction history for computing purchase features",
    # For S3:
    # path="s3://bucket/user_transactions.parquet",
    # For BigQuery:
    # table="project.dataset.user_transactions",
)


# =============================================================================
# USER PROFILE DATA SOURCE
# =============================================================================
# Static user profile information (demographics, account age, etc.)

user_profile_source = FileSource(
    name="user_profiles",
    path="data/user_profiles.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
    description="User profile and demographic features",
)


# =============================================================================
# PRODUCT DATA SOURCE
# =============================================================================
# Product catalog and metadata

product_source = FileSource(
    name="products",
    path="data/products.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
    description="Product catalog features",
)


# =============================================================================
# PRODUCT STATS DATA SOURCE
# =============================================================================
# Aggregated product statistics (ratings, views, sales)

product_stats_source = FileSource(
    name="product_stats",
    path="data/product_stats.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
    description="Product statistics and popularity metrics",
)


# =============================================================================
# STORE DATA SOURCE
# =============================================================================
# Store/dealer information

store_source = FileSource(
    name="stores",
    path="data/stores.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
    description="Store and dealer information",
)


# =============================================================================
# PUSH SOURCE (for real-time features)
# =============================================================================
# Allows pushing features directly without going through offline store
# Useful for real-time computed features

user_realtime_source = PushSource(
    name="user_realtime",
    batch_source=user_transactions_source,  # Fallback for historical queries
    description="Real-time user activity features pushed from streaming",
)


# =============================================================================
# STREAMING SOURCE EXAMPLE (Kafka)
# =============================================================================
# For production streaming use cases:
#
# from feast import KafkaSource
# 
# user_events_stream = KafkaSource(
#     name="user_events_stream",
#     kafka_bootstrap_servers="localhost:9092",
#     topic="user_events",
#     timestamp_field="event_timestamp",
#     batch_source=user_transactions_source,
#     message_format=AvroFormat(
#         schema_json="""
#         {
#             "type": "record",
#             "name": "UserEvent",
#             "fields": [
#                 {"name": "user_id", "type": "string"},
#                 {"name": "event_type", "type": "string"},
#                 {"name": "amount", "type": "float"},
#                 {"name": "event_timestamp", "type": "long"}
#             ]
#         }
#         """
#     ),
# )
