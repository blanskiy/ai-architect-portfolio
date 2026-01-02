# Project 1: Feature Store with Feast

Implement a production feature store for consistent feature engineering across training and serving.

## Overview

| Aspect | Details |
|--------|---------|
| **Purpose** | Eliminate training-serving skew, enable feature reuse |
| **Technology** | Feast, Redis (online), Parquet (offline) |
| **Key Concepts** | Feature views, entities, materialization, point-in-time joins |

## The Problem

### Without a Feature Store

```python
# Training (data scientist)
df = spark.sql("""
    SELECT user_id,
           AVG(purchase_amount) as avg_purchase,  -- Last 30 days
           COUNT(*) as purchase_count
    FROM transactions
    WHERE date BETWEEN '2024-01-01' AND '2024-01-31'
    GROUP BY user_id
""")

# Serving (engineer) - DIFFERENT LOGIC!
def get_features(user_id):
    recent = db.query(f"SELECT * FROM transactions WHERE user_id={user_id}")
    return {
        'avg_purchase': sum(r.amount for r in recent) / len(recent),  # All time!
        'purchase_count': len(recent)  # Different window!
    }
```

**Result**: Training-serving skew → model performs differently in production!

### With a Feature Store

```python
# Training
training_df = store.get_historical_features(
    entity_df=entity_df,
    features=["user_features:avg_purchase_30d", "user_features:purchase_count_30d"]
)

# Serving - SAME FEATURES!
online_features = store.get_online_features(
    entity_rows=[{"user_id": "user123"}],
    features=["user_features:avg_purchase_30d", "user_features:purchase_count_30d"]
)
```

**Result**: Consistent features → reliable model performance!

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FEATURE STORE ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   DATA SOURCES                                                               │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐                                 │
│   │Transactions│ │User Data │  │ Events   │                                 │
│   │  (Kafka)  │  │ (DB)     │  │ (Stream) │                                 │
│   └─────┬─────┘  └────┬─────┘  └────┬─────┘                                 │
│         │             │             │                                        │
│         └─────────────┼─────────────┘                                        │
│                       │                                                      │
│                       ▼                                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    FEATURE ENGINEERING                               │  │
│   │                    (Spark, Pandas, SQL)                              │  │
│   │                                                                      │  │
│   │   user_features:                                                     │  │
│   │   - avg_purchase_30d                                                 │  │
│   │   - purchase_count_30d                                               │  │
│   │   - days_since_last_purchase                                         │  │
│   │                                                                      │  │
│   │   product_features:                                                  │  │
│   │   - avg_rating                                                       │  │
│   │   - view_count_7d                                                    │  │
│   └─────────────────────────────────┬───────────────────────────────────┘  │
│                                     │                                        │
│              ┌──────────────────────┴──────────────────────┐                │
│              │                                             │                │
│              ▼                                             ▼                │
│   ┌─────────────────────────┐               ┌─────────────────────────┐    │
│   │      OFFLINE STORE      │               │      ONLINE STORE       │    │
│   │                         │               │                         │    │
│   │   • Parquet files       │  Materialize  │   • Redis               │    │
│   │   • BigQuery            │ ───────────►  │   • DynamoDB            │    │
│   │   • Snowflake           │               │   • Cassandra           │    │
│   │                         │               │                         │    │
│   │   For: Training         │               │   For: Serving          │    │
│   │   Latency: Seconds      │               │   Latency: <10ms        │    │
│   └────────────┬────────────┘               └────────────┬────────────┘    │
│                │                                         │                  │
│                ▼                                         ▼                  │
│   ┌─────────────────────────┐               ┌─────────────────────────┐    │
│   │   TRAINING PIPELINE     │               │   INFERENCE SERVICE     │    │
│   │                         │               │                         │    │
│   │   get_historical_       │               │   get_online_           │    │
│   │   features()            │               │   features()            │    │
│   │                         │               │                         │    │
│   │   Point-in-time joins   │               │   Low-latency lookup    │    │
│   └─────────────────────────┘               └─────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
project1-feature-store/
├── README.md
├── INTERVIEW_PREP.md
├── requirements.txt
├── feature_repo/
│   ├── feature_store.yaml      # Feast configuration
│   ├── entities.py             # Entity definitions
│   ├── features.py             # Feature view definitions
│   └── data_sources.py         # Data source configurations
├── src/
│   ├── feature_engineering.py  # Feature computation logic
│   ├── materialization.py      # Offline → Online sync
│   ├── training_data.py        # Historical feature retrieval
│   └── online_serving.py       # Real-time feature serving
├── data/
│   └── sample_data.py          # Generate sample data
├── notebooks/
│   └── feature_exploration.ipynb
└── tests/
    ├── test_features.py
    └── test_serving.py
```

## Key Concepts

### 1. Entities

The primary key for feature lookup:

```python
from feast import Entity

user = Entity(
    name="user_id",
    description="Unique user identifier",
)

product = Entity(
    name="product_id", 
    description="Unique product identifier",
)
```

### 2. Feature Views

Logical grouping of related features:

```python
from feast import FeatureView, Field
from feast.types import Float32, Int64

user_features = FeatureView(
    name="user_features",
    entities=[user],
    schema=[
        Field(name="avg_purchase_30d", dtype=Float32),
        Field(name="purchase_count_30d", dtype=Int64),
        Field(name="days_since_last_purchase", dtype=Int64),
    ],
    source=user_transactions_source,
    online=True,
    ttl=timedelta(days=1),
)
```

### 3. Point-in-Time Joins

Prevent data leakage by joining features at the correct timestamp:

```
Entity DataFrame:
┌─────────┬─────────────────────┐
│ user_id │ event_timestamp     │
├─────────┼─────────────────────┤
│ user_1  │ 2024-01-15 10:00:00 │  ← Want features AS OF this time
│ user_2  │ 2024-01-16 14:00:00 │
└─────────┴─────────────────────┘

Feature Store has:
┌─────────┬─────────────────────┬───────────────┐
│ user_id │ timestamp           │ avg_purchase  │
├─────────┼─────────────────────┼───────────────┤
│ user_1  │ 2024-01-10 00:00:00 │ 50.00         │  ← Use this (before event)
│ user_1  │ 2024-01-20 00:00:00 │ 75.00         │  ← Don't use (after event = leakage!)
└─────────┴─────────────────────┴───────────────┘
```

### 4. Materialization

Sync features from offline to online store:

```python
# Materialize features to online store
store.materialize(
    start_date=datetime(2024, 1, 1),
    end_date=datetime.now(),
)

# Or incrementally
store.materialize_incremental(end_date=datetime.now())
```

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Feature Store
```bash
cd feature_repo
feast apply
```

### 3. Generate Sample Data
```python
python data/sample_data.py
```

### 4. Materialize Features
```python
python src/materialization.py
```

### 5. Retrieve Features for Training
```python
from src.training_data import get_training_features

df = get_training_features(
    entity_df=my_entities,
    features=["user_features:avg_purchase_30d"]
)
```

### 6. Serve Features Online
```python
from src.online_serving import get_online_features

features = get_online_features(user_id="user_123")
```

## Interview Talking Points

### Q: "What is a feature store and why do you need one?"

> "A feature store is a centralized repository for storing, managing, and serving ML features. It solves three main problems: (1) training-serving skew by ensuring the same feature logic is used everywhere, (2) feature reuse across teams instead of rebuilding the same features, and (3) point-in-time correctness to prevent data leakage during training. We use Feast with Redis for low-latency online serving."

### Q: "How do you prevent data leakage?"

> "Point-in-time joins. When creating training data, features are joined based on their timestamp relative to the label event. If a user made a purchase on Jan 15th, I only use features computed BEFORE Jan 15th. The feature store handles this automatically by maintaining feature timestamps."

### Q: "How does online vs offline serving work?"

> "Offline store (Parquet, BigQuery) holds historical features for training - high latency is fine. Online store (Redis, DynamoDB) holds the latest feature values for real-time inference - sub-10ms latency. Materialization syncs features from offline to online on a schedule."

---

*Project 1 - Advanced ML Systems*
