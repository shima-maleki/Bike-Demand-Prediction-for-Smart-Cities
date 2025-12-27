# Chapter 11: Design Decisions & Architecture

## Overview

This chapter explains **why** we made specific technical choices throughout the project. Understanding these decisions will help you:
- Make informed choices in your own projects
- Explain your architecture in interviews
- Adapt this system to different use cases

## Core Architectural Decisions

### 1. Docker-First Architecture

**Decision**: All services run in Docker containers orchestrated with Docker Compose

**Why?**
- ✅ **Reproducibility**: Works identically on your laptop, CI, and production
- ✅ **Isolation**: Each service has its own environment, no dependency conflicts
- ✅ **Portability**: Deploy to any cloud (AWS, GCP, Azure) or on-premise
- ✅ **Development Speed**: New team members productive in <10 minutes
- ✅ **Version Control**: Infrastructure defined in code

**Alternatives Considered:**
| Alternative | Why Not Chosen |
|-------------|----------------|
| **Virtual Machines** | Too heavy, slow startup, resource-intensive |
| **Conda Environments** | Doesn't handle multi-service orchestration |
| **Kubernetes** | Overkill for this scale, adds unnecessary complexity |

**Trade-offs:**
- ❌ **Docker Desktop Required**: Team must install Docker
- ❌ **Resource Overhead**: ~2GB RAM for containers
- ✅ **But**: Simplifies deployment dramatically

---

### 2. PostgreSQL as Primary Database

**Decision**: Use PostgreSQL instead of specialized time-series databases

**Why?**
- ✅ **Mature & Battle-Tested**: 30+ years of development
- ✅ **JSONB Support**: Store flexible feature vectors
- ✅ **Rich Query Capabilities**: Complex JOINs, window functions
- ✅ **ACID Guarantees**: Data consistency for financial reporting
- ✅ **Free & Open Source**: No licensing costs
- ✅ **Excellent Performance**: Handles millions of rows easily

**Alternatives Considered:**
| Database | Why Not Chosen |
|----------|----------------|
| **TimescaleDB** | Adds complexity, PostgreSQL sufficient for our scale |
| **InfluxDB** | Limited JOIN support, no JSONB |
| **MongoDB** | Weaker consistency guarantees, harder querying |
| **Cassandra** | Over-engineered for single-city deployment |

**Benchmarks (our dataset: 50K rows):**
- Query latest status for all stations: **<50ms**
- Aggregate hourly demand: **<100ms**
- JOIN bikes + weather + features: **<200ms**

**When to Switch:**
- Data exceeds 100M rows: Consider TimescaleDB
- Multi-region deployment: Consider Cassandra
- Real-time streaming: Add Apache Kafka

---

### 3. JSONB for Feature Storage

**Decision**: Store engineered features as JSONB, not individual columns

**Schema:**
```sql
CREATE TABLE features (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(50),
    timestamp TIMESTAMP,
    feature_json JSONB,  -- ← All features here
    feature_version VARCHAR(20)
);
```

**Why?**
- ✅ **Flexibility**: Add/remove features without schema migrations
- ✅ **Versioning**: Store multiple feature versions side-by-side
- ✅ **Reproducibility**: Exact features used for training stored with model
- ✅ **Performance**: GIN indexes allow fast JSON queries
- ✅ **Debugging**: Easy to inspect what the model saw

**Alternatives Considered:**
| Approach | Why Not Chosen |
|----------|----------------|
| **Individual Columns** | Requires migration for every new feature |
| **Pickle Binary Blobs** | Not queryable, hard to debug |
| **Separate Feature Store** (Feast) | Adds operational complexity |

**Example Feature JSON:**
```json
{
  "hour_of_day": 14,
  "day_of_week": 3,
  "is_weekend": 0,
  "bikes_lag_1h": 15,
  "bikes_rolling_mean_3h": 14.5,
  "temperature": 22.5,
  "is_holiday": 0
}
```

**Query Performance:**
```sql
-- Extract specific feature (< 10ms with GIN index)
SELECT feature_json->>'temperature' AS temp
FROM features
WHERE feature_version = 'v1.0'
LIMIT 1000;
```

---

### 4. XGBoost & LightGBM (Not Deep Learning)

**Decision**: Use gradient boosting trees, not neural networks

**Why?**
- ✅ **Tabular Data**: Tree models excel on structured features
- ✅ **Interpretability**: Feature importance easily extracted
- ✅ **Training Speed**: Minutes vs hours for neural networks
- ✅ **Less Data Required**: Effective with 10K samples
- ✅ **Robustness**: Less hyperparameter sensitivity

**Benchmark Results:**
| Model | RMSE | Training Time | Hyperparameters |
|-------|------|---------------|-----------------|
| **LightGBM** | 0.51 | 2 min | 5 tuned |
| **XGBoost** | 0.56 | 3 min | 5 tuned |
| LSTM | 0.68 | 45 min | 15+ tuned |
| Prophet | 0.89 | 8 min | 3 tuned |

**When Deep Learning Makes Sense:**
- **Images**: CNN for bike availability from camera feeds
- **Text**: NLP for user reviews/complaints
- **Very Long Sequences**: LSTM for multi-day patterns
- **Transfer Learning**: Pre-trained models available

**Our Use Case**: Hourly forecasts with 22 features → Gradient boosting wins

---

### 5. MLflow for Experiment Tracking

**Decision**: Use MLflow instead of Weights & Biases, Comet, or Neptune

**Why?**
- ✅ **Open Source**: No vendor lock-in, free forever
- ✅ **Self-Hosted**: Data stays on our infrastructure
- ✅ **Model Registry**: Built-in staging/production promotion
- ✅ **Language Agnostic**: Works with Python, R, Java
- ✅ **Simple Setup**: Single Docker container

**Features We Use:**
1. **Experiment Tracking**: Log metrics, params, artifacts
2. **Model Registry**: Version models, promote to production
3. **Model Serving**: Load models by version/stage
4. **Artifact Storage**: Save plots, feature importance

**Alternatives Considered:**
| Tool | Why Not Chosen |
|------|----------------|
| **Weights & Biases** | Requires cloud account, data privacy concerns |
| **Comet.ml** | Free tier limited, vendor lock-in |
| **Neptune.ai** | Expensive for commercial use |
| **TensorBoard** | Designed for TensorFlow, harder for XGBoost |

**MLflow Workflow:**
```python
import mlflow

# Start run
with mlflow.start_run(run_name="lightgbm-v1"):
    # Log parameters
    mlflow.log_param("max_depth", 6)
    mlflow.log_param("learning_rate", 0.1)

    # Train model
    model.fit(X_train, y_train)

    # Log metrics
    mlflow.log_metric("rmse", 0.51)
    mlflow.log_metric("r2", 0.511)

    # Log model
    mlflow.sklearn.log_model(model, "model")

    # Register model
    mlflow.register_model("runs:/abc123/model", "bike-demand-forecaster")
```

---

### 6. Apache Airflow for Orchestration

**Decision**: Use Airflow instead of Prefect, Dagster, or Cron jobs

**Why?**
- ✅ **Industry Standard**: Used by Airbnb, Uber, Robinhood
- ✅ **DAG-Based**: Visual workflow representation
- ✅ **Rich UI**: Monitor, retry, backfill from web interface
- ✅ **Extensive Integrations**: 100+ providers (Postgres, AWS, etc.)
- ✅ **Python-Native**: Write workflows in Python

**Alternatives Considered:**
| Tool | Why Not Chosen |
|------|----------------|
| **Prefect** | Newer, smaller community, less mature |
| **Dagster** | Great but complex, learning curve steep |
| **Cron Jobs** | No dependency management, hard to monitor |
| **AWS Step Functions** | Vendor lock-in, requires AWS |

**Our DAGs:**
1. **Data Ingestion** (every 15 min): Fetch bike data
2. **Weather Enrichment** (every 30 min): Get weather
3. **Feature Engineering** (hourly): Generate features
4. **Model Training** (daily): Train and evaluate

**Airflow Advantages:**
- **Dependency Management**: "Weather DAG depends on Data DAG"
- **Retry Logic**: Auto-retry failed tasks with exponential backoff
- **Alerting**: Email/Slack on failures
- **Backfilling**: Re-run historical data easily

---

### 7. FastAPI for Model Serving

**Decision**: Use FastAPI instead of Flask, Django, or dedicated serving tools

**Why?**
- ✅ **High Performance**: Async support, 3x faster than Flask
- ✅ **Auto-Generated Docs**: OpenAPI/Swagger UI built-in
- ✅ **Type Safety**: Pydantic models prevent bugs
- ✅ **Modern**: Based on Python 3.7+ type hints
- ✅ **Production-Ready**: Used by Microsoft, Netflix, Uber

**Benchmark (1000 requests, single worker):**
| Framework | Requests/sec | Latency (p95) |
|-----------|-------------|---------------|
| **FastAPI** | 1,200 | 45ms |
| Flask | 400 | 120ms |
| Django | 350 | 150ms |

**Alternatives Considered:**
| Tool | Why Not Chosen |
|------|----------------|
| **Flask** | Synchronous, slower, no auto-docs |
| **Django** | Heavyweight, designed for full web apps |
| **TensorFlow Serving** | Limited to TensorFlow models |
| **TorchServe** | Limited to PyTorch models |
| **BentoML** | Great but adds abstraction layer |

**FastAPI Features We Use:**
- **Pydantic Models**: Input validation
- **Async Endpoints**: Non-blocking I/O
- **Dependency Injection**: Database connections
- **Background Tasks**: Async predictions
- **OpenAPI**: Auto-generated API documentation

---

### 8. Streamlit for Dashboard

**Decision**: Use Streamlit instead of React, Dash, or Tableau

**Why?**
- ✅ **Pure Python**: No JavaScript required
- ✅ **Rapid Prototyping**: Dashboard in <1 hour
- ✅ **Interactive Widgets**: Sliders, dropdowns built-in
- ✅ **Easy Deployment**: Single command (`streamlit run`)
- ✅ **Real-Time Updates**: WebSocket-based reactivity

**Alternatives Considered:**
| Tool | Why Not Chosen |
|------|----------------|
| **React + D3.js** | Requires frontend expertise, much slower |
| **Plotly Dash** | More verbose, steeper learning curve |
| **Tableau** | Expensive, not code-based |
| **Grafana** | Designed for metrics, not ML dashboards |

**Streamlit Limitations (and solutions):**
- **Stateless by default**: Use `st.session_state` for persistence
- **Single-threaded**: Cache expensive computations with `@st.cache_data`
- **Limited styling**: Use custom CSS or migrate to React later

**Our Dashboard Pages:**
1. **Demand Forecast**: Interactive predictions
2. **Model Performance**: Metrics over time
3. **Data Quality**: Pipeline health
4. **System Health**: Infrastructure monitoring

---

### 9. GitHub Actions for CI/CD

**Decision**: Use GitHub Actions instead of Jenkins, CircleCI, or GitLab CI

**Why?**
- ✅ **Native Integration**: Built into GitHub
- ✅ **Free for Public Repos**: Unlimited build minutes
- ✅ **Simple YAML**: Easy to learn and maintain
- ✅ **Marketplace**: 10K+ pre-built actions
- ✅ **Matrix Builds**: Test across OS/Python versions

**Alternatives Considered:**
| Tool | Why Not Chosen |
|------|----------------|
| **Jenkins** | Requires hosting, complex setup |
| **CircleCI** | Free tier limited (1000 min/month) |
| **GitLab CI** | Requires migrating to GitLab |
| **Travis CI** | Deprecated for open-source |

**Our Workflows:**
1. **CI**: Lint, test, build Docker images
2. **CD**: Push to registry, deploy
3. **Model Training**: Automated retraining

---

### 10. Time-Series Train/Val/Test Split

**Decision**: Split by time, never shuffle

**Our Split:**
```python
# Chronological split (no shuffling!)
train = data[data['timestamp'] < '2023-09-01']  # 70%
val   = data[data['timestamp'].between('2023-09-01', '2023-10-01')]  # 15%
test  = data[data['timestamp'] > '2023-10-01']  # 15%
```

**Why?**
- ✅ **Prevents Data Leakage**: Model can't see future
- ✅ **Realistic Evaluation**: Tests on truly unseen data
- ✅ **Mimics Production**: New data always comes later

**Common Mistake (DON'T DO THIS):**
```python
# ❌ WRONG: Random shuffle leaks future into training
from sklearn.model_selection import train_test_split
X_train, X_test = train_test_split(X, y, shuffle=True)  # BAD!
```

**Why This Matters:**
Imagine training on September data and testing on August data:
- Model learns "September has low demand" (back-to-school)
- Predicts low demand for August
- Reality: August is summer peak season
- Model fails in production!

---

## Key Takeaways

### When to Use This Architecture
✅ **Perfect For:**
- Tabular time-series forecasting
- Single-city deployment (< 100M rows)
- Team of 1-10 engineers
- MVP or production system
- Budget: $0 (open-source tools)

❌ **Not Ideal For:**
- Image/video processing (use CNNs)
- Real-time streaming (<1s latency) (add Kafka)
- Global scale (100B+ rows) (use Cassandra/Spark)
- Regulatory requirements (HIPAA/SOC2) (add encryption, audit logs)

### Scalability Path

**Current (Level 2 MLOps):**
- 1 city, 50K rows, Docker Compose

**Next Steps (Level 3 MLOps):**
1. **Multi-City**: Partition database by city_id
2. **Kubernetes**: Replace Docker Compose for auto-scaling
3. **Feature Store**: Add Feast for online/offline features
4. **Streaming**: Add Kafka for real-time ingestion
5. **A/B Testing**: Serve multiple models, compare performance

---

## Interview Talking Points

Use these explanations to showcase your architectural thinking:

1. **"I chose XGBoost over deep learning because gradient boosting achieves 25% lower RMSE on tabular data with 10x faster training"**

2. **"I used JSONB for features instead of individual columns to avoid schema migrations every time we add a feature - critical for rapid experimentation"**

3. **"I implemented time-based train/test split to prevent data leakage - a common mistake in time-series projects that leads to overly optimistic metrics"**

4. **"I chose FastAPI over Flask for 3x better performance and auto-generated API documentation, which is essential for team collaboration"**

5. **"I used Docker Compose over Kubernetes because it's simpler for single-node deployment, with a clear migration path to K8s when we need auto-scaling"**

---

**Next**: [Chapter 12: Production Deployment](12-production.md)
