# Feature Store - Interview Cheat Sheet

## Quick Framework (30-second answer)

> "A feature store is a centralized system for managing ML features across training and serving. It solves three problems: **training-serving skew** by ensuring identical feature computation, **feature reuse** across teams, and **point-in-time correctness** to prevent data leakage. I use Feast with Redis for sub-10ms online serving and Parquet for offline training. Features are materialized on a schedule to sync offline → online."

---

## The Problem It Solves

### Training-Serving Skew

```
WITHOUT Feature Store:
───────────────────────────────────────────────────────
Training:  SELECT AVG(amount) FROM txns WHERE date > '2024-01-01'
Serving:   recent_txns.mean()  # Different code path!
Result:    Model sees different data in prod → 🔥 degraded performance

WITH Feature Store:
───────────────────────────────────────────────────────
Training:  store.get_historical_features(entity_df, ["user:avg_purchase"])
Serving:   store.get_online_features({"user_id": "123"}, ["user:avg_purchase"])
Result:    Identical features → consistent model behavior ✓
```

---

## Architecture (Draw This!)

```
┌─────────────────────────────────────────────────────────────────┐
│                     FEATURE STORE                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   RAW DATA                                                       │
│   ┌────────┐  ┌────────┐  ┌────────┐                           │
│   │ Events │  │  DB    │  │ Stream │                           │
│   └───┬────┘  └───┬────┘  └───┬────┘                           │
│       └───────────┼───────────┘                                 │
│                   ▼                                              │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │              FEATURE ENGINEERING                         │  │
│   │              (Spark, Pandas, dbt)                        │  │
│   └────────────────────────┬────────────────────────────────┘  │
│                            │                                    │
│            ┌───────────────┴───────────────┐                   │
│            ▼                               ▼                    │
│   ┌─────────────────┐           ┌─────────────────┐           │
│   │  OFFLINE STORE  │           │  ONLINE STORE   │           │
│   │                 │           │                 │           │
│   │  • Parquet      │  Materialize  │  • Redis       │           │
│   │  • BigQuery     │ ──────────►  │  • DynamoDB    │           │
│   │  • Snowflake    │           │                 │           │
│   │                 │           │                 │           │
│   │  Latency: ~sec  │           │  Latency: <10ms │           │
│   └────────┬────────┘           └────────┬────────┘           │
│            │                             │                     │
│            ▼                             ▼                     │
│   ┌─────────────────┐           ┌─────────────────┐           │
│   │    TRAINING     │           │    INFERENCE    │           │
│   │                 │           │                 │           │
│   │ Point-in-time   │           │ Real-time       │           │
│   │ feature joins   │           │ feature lookup  │           │
│   └─────────────────┘           └─────────────────┘           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Concepts (Memorize!)

### 1. Entity
Primary key for feature lookup.

```python
user = Entity(name="user_id")
product = Entity(name="product_id")
```

### 2. Feature View
Logical grouping of related features.

```python
user_features = FeatureView(
    name="user_features",
    entities=[user],
    schema=[
        Field(name="avg_purchase_30d", dtype=Float32),
        Field(name="purchase_count_30d", dtype=Int64),
    ],
    source=user_transactions_source,
    online=True,  # Enable online serving
    ttl=timedelta(days=1),
)
```

### 3. Point-in-Time Join
Prevent data leakage by using features as of the event time.

```
Entity DF:
┌─────────┬─────────────────────┬───────┐
│ user_id │ event_timestamp     │ label │
├─────────┼─────────────────────┼───────┤
│ user_1  │ 2024-01-15 10:00:00 │ 1     │
└─────────┴─────────────────────┴───────┘

Feature Store joins features valid BEFORE 2024-01-15 10:00:00
(not after - that would be leakage!)
```

### 4. Materialization
Copy features from offline → online store.

```python
# Full materialization
store.materialize(start_date, end_date)

# Incremental (since last run)
store.materialize_incremental(end_date)
```

---

## Online vs Offline

| Aspect | Offline Store | Online Store |
|--------|---------------|--------------|
| **Purpose** | Training | Inference |
| **Latency** | Seconds | <10ms |
| **Technology** | Parquet, BigQuery | Redis, DynamoDB |
| **Data** | Historical | Latest values only |
| **Query** | Point-in-time joins | Key-value lookup |

---

## Common Interview Questions

### Q: "What is a feature store and why do you need one?"

> "A feature store centralizes ML feature management. It ensures **training-serving consistency** by using the same feature definitions everywhere, enables **feature reuse** across teams instead of rebuilding, and handles **point-in-time correctness** to prevent data leakage. The offline store serves training, the online store serves inference with sub-10ms latency."

### Q: "How do you prevent data leakage?"

> "Point-in-time joins. When building training data, I provide an entity dataframe with timestamps for each label event. The feature store joins only features that were valid BEFORE each timestamp. For example, if predicting whether user_123 will purchase on Jan 15, I only use features computed before Jan 15 - never features computed after, which would be leakage."

### Q: "How does materialization work?"

> "Materialization copies features from the offline store (Parquet, BigQuery) to the online store (Redis) so they can be served with low latency. I typically run incremental materialization hourly for frequently changing features, daily for slower features. The TTL setting determines how long features stay valid in the online store."

### Q: "What's the difference between batch and real-time features?"

> "Batch features are pre-computed periodically (hourly/daily) and stored - things like 30-day averages. Real-time features are computed at request time - like 'time since last click' that depends on the exact request moment. I use on-demand feature views for real-time computed features, but most features are batch for performance."

### Q: "How do you handle feature freshness vs latency tradeoff?"

> "It depends on the use case. For features that change slowly (user demographics), daily materialization is fine. For features that need to reflect recent behavior (last 5 purchases), I materialize hourly. For truly real-time features (seconds-old data), I use streaming ingestion with Kafka → online store, or compute on-demand at serving time."

### Q: "How do you handle schema changes?"

> "Feature versioning. If I change a feature definition significantly, I create a new feature version (avg_purchase_v2) rather than modifying in place. This ensures models trained on v1 continue to get v1 features. I deprecate old versions gradually after all models migrate."

---

## Design Questions

### Q: "Design a feature store for a recommendation system"

**Requirements:**
- 100M users, 1M products
- 10K QPS for recommendations
- Features: user history, product stats, real-time signals

**Design:**

```
1. ENTITIES
   - user_id → user features
   - product_id → product features
   - (user_id, product_id) → interaction features

2. FEATURE VIEWS
   User Features (hourly refresh):
   - purchase_count_30d
   - avg_order_value
   - favorite_categories
   
   Product Features (daily refresh):
   - avg_rating
   - purchase_velocity
   - inventory_status
   
   Real-time Features (streaming):
   - last_viewed_products (Kafka → Redis)
   - session_click_count

3. ONLINE STORE
   - Redis Cluster for 10K QPS
   - 100M users × 10 features × 8 bytes ≈ 8GB user features
   - 1M products × 20 features × 8 bytes ≈ 160MB product features
   - Total: ~10GB Redis (fits in memory)

4. SERVING PATTERN
   Request → Get user features (1 lookup)
           → Get candidate product features (batch lookup)
           → Model inference
           → Return ranked products
   
   Latency budget: 10ms features + 20ms model = <50ms total
```

---

## Key Numbers

| Metric | Target |
|--------|--------|
| Online serving latency | <10ms |
| Materialization frequency | Hourly (active), Daily (stable) |
| Feature freshness | <1 hour for most features |
| Online store size | Fits in memory (Redis) |

---

## Red Flags to Avoid

❌ "We compute features differently in training vs serving"
   → Training-serving skew guaranteed

❌ "We just use the latest feature values for training"
   → Data leakage - using future information

❌ "Each team maintains their own feature pipelines"
   → Duplication, inconsistency, wasted effort

❌ "We query the database at serving time"
   → High latency, database pressure

✅ "Same feature definition serves training and inference"
✅ "Point-in-time joins prevent leakage"
✅ "Features are shared across teams via the registry"
✅ "Pre-computed features enable sub-10ms serving"

---

## Tools to Mention

| Tool | Type | Best For |
|------|------|----------|
| **Feast** | Open source | General purpose, flexible |
| **Tecton** | Managed | Enterprise, streaming |
| **Databricks Feature Store** | Managed | Databricks ecosystem |
| **AWS SageMaker Feature Store** | Managed | AWS ecosystem |
| **Vertex AI Feature Store** | Managed | GCP ecosystem |
| **Azure ML Feature Store** | Managed | Azure ecosystem |
