# Chapter 9: Monitoring & Observability

## Overview

This chapter guides you through implementing comprehensive monitoring for your ML system - data drift detection, model performance tracking, and system observability.

**What You'll Build**:
- Data drift detection with Evidently AI
- Model performance monitoring
- API metrics with Prometheus
- Real-time dashboards with Grafana
- Automated alerting for degradation

**Estimated Time**: 3-4 hours

## Why Monitoring Matters

**The Problem**: ML models degrade over time due to:
- **Data drift**: Input features change (e.g., bike usage patterns change post-pandemic)
- **Concept drift**: Target relationship changes (e.g., new bike lanes alter demand)
- **System issues**: API latency, database slowdowns, model serving errors

**Without Monitoring**: Models fail silently, predictions become inaccurate, users lose trust.

**With Monitoring**: Detect issues early, retrain proactively, maintain 99%+ uptime.

---

## Monitoring Layers

```
┌─────────────────────────────────────────────┐
│  LAYER 1: Data Monitoring                  │
│  - Feature drift (Evidently AI)             │
│  - Target drift                             │
│  - Missing data                             │
│  - Data quality checks                      │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│  LAYER 2: Model Monitoring                 │
│  - RMSE, MAE, MAPE tracking                │
│  - Prediction confidence                    │
│  - Model version tracking                   │
│  - Feature importance shifts                │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│  LAYER 3: System Monitoring                │
│  - API latency (Prometheus)                 │
│  - Throughput (requests/sec)                │
│  - Error rates                              │
│  - Database performance                     │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│  LAYER 4: Alerting                         │
│  - Slack/Email notifications                │
│  - PagerDuty for critical issues            │
│  - Automated retraining triggers            │
└─────────────────────────────────────────────┘
```

---

## Step 1: Data Drift Detection with Evidently AI

### Why Evidently AI?

**Decision**: Evidently vs. Alibi Detect vs. Custom

**Why Evidently Won**:
- **Pre-built Reports**: Beautiful HTML reports out-of-the-box
- **Statistical Tests**: Kolmogorov-Smirnov, PSI, Jensen-Shannon divergence
- **ML-First**: Designed specifically for ML monitoring
- **Open Source**: Free for self-hosted deployments
- **Easy Integration**: Works with pandas DataFrames

### `src/monitoring/data_drift_detector.py`

```python
"""
Data drift detection using Evidently AI

Detects when input feature distributions change significantly
"""

from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, DataQualityPreset
from evidently.metrics import DatasetDriftMetric, ColumnDriftMetric
import pandas as pd
import logging
from typing import Dict, List
from datetime import datetime
import json

class DataDriftDetector:
    def __init__(self, reference_data: pd.DataFrame):
        """
        Initialize drift detector with reference data (baseline)

        Args:
            reference_data: Training data to use as reference
        """
        self.reference_data = reference_data
        self.logger = logging.getLogger(__name__)

    def detect_drift(
        self,
        current_data: pd.DataFrame,
        feature_columns: List[str],
        drift_threshold: float = 0.5
    ) -> Dict:
        """
        Detect drift between reference and current data

        Args:
            current_data: Recent production data
            feature_columns: Columns to check for drift
            drift_threshold: Statistical test p-value threshold

        Returns:
            Dict with drift results
        """
        self.logger.info(f"Checking drift for {len(feature_columns)} features")

        # Create Evidently report
        report = Report(metrics=[
            DataDriftPreset(drift_share=drift_threshold),
            DataQualityPreset()
        ])

        # Run report
        report.run(
            reference_data=self.reference_data[feature_columns],
            current_data=current_data[feature_columns]
        )

        # Extract results
        drift_results = report.as_dict()

        # Parse drift metrics
        dataset_drift = drift_results['metrics'][0]['result']['dataset_drift']
        drift_by_columns = drift_results['metrics'][0]['result']['drift_by_columns']

        drifted_features = [
            col for col, metrics in drift_by_columns.items()
            if metrics['drift_detected']
        ]

        drift_summary = {
            'timestamp': datetime.now().isoformat(),
            'dataset_drift_detected': dataset_drift,
            'num_drifted_features': len(drifted_features),
            'total_features': len(feature_columns),
            'drift_share': len(drifted_features) / len(feature_columns),
            'drifted_features': drifted_features,
            'drift_details': drift_by_columns
        }

        if dataset_drift:
            self.logger.warning(
                f"⚠️ DRIFT DETECTED: {len(drifted_features)}/{len(feature_columns)} features drifted"
            )
            for feature in drifted_features:
                self.logger.warning(f"  - {feature}: drift score = {drift_by_columns[feature]['drift_score']:.3f}")
        else:
            self.logger.info("✅ No significant drift detected")

        return drift_summary

    def generate_html_report(
        self,
        current_data: pd.DataFrame,
        feature_columns: List[str],
        output_path: str = "reports/drift_report.html"
    ):
        """
        Generate visual HTML drift report

        Args:
            current_data: Current production data
            feature_columns: Features to analyze
            output_path: Path to save HTML report
        """
        report = Report(metrics=[
            DataDriftPreset(),
            DataQualityPreset()
        ])

        report.run(
            reference_data=self.reference_data[feature_columns],
            current_data=current_data[feature_columns]
        )

        report.save_html(output_path)

        self.logger.info(f"Drift report saved to {output_path}")

    def save_drift_to_database(self, drift_summary: Dict, db_connection):
        """
        Save drift metrics to PostgreSQL for tracking over time

        Args:
            drift_summary: Drift detection results
            db_connection: PostgreSQL connection
        """
        cursor = db_connection.cursor()

        insert_query = """
        INSERT INTO data_drift_metrics (
            timestamp,
            dataset_drift_detected,
            drift_share,
            num_drifted_features,
            drifted_features,
            drift_details
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        cursor.execute(insert_query, (
            datetime.fromisoformat(drift_summary['timestamp']),
            drift_summary['dataset_drift_detected'],
            drift_summary['drift_share'],
            drift_summary['num_drifted_features'],
            json.dumps(drift_summary['drifted_features']),
            json.dumps(drift_summary['drift_details'])
        ))

        db_connection.commit()
        cursor.close()

        self.logger.info("Drift metrics saved to database")


# Example usage
if __name__ == "__main__":
    import psycopg2

    # Load reference data (training set)
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="bike_demand_db",
        user="postgres",
        password="postgres"
    )

    query_train = """
    SELECT * FROM features
    WHERE timestamp BETWEEN '2024-01-01' AND '2024-01-31'
    LIMIT 10000
    """

    reference_df = pd.read_sql_query(query_train, conn)

    # Load current data (last 7 days)
    query_current = """
    SELECT * FROM features
    WHERE timestamp >= NOW() - INTERVAL '7 days'
    LIMIT 10000
    """

    current_df = pd.read_sql_query(query_current, conn)

    # Feature columns
    feature_cols = [
        'hour_of_day', 'day_of_week', 'is_weekend',
        'bikes_lag_1h', 'bikes_lag_24h',
        'bikes_rolling_mean_3h', 'temperature', 'humidity'
    ]

    # Detect drift
    detector = DataDriftDetector(reference_data=reference_df)
    drift_results = detector.detect_drift(
        current_data=current_df,
        feature_columns=feature_cols
    )

    # Generate HTML report
    detector.generate_html_report(
        current_data=current_df,
        feature_columns=feature_cols,
        output_path="reports/drift_report.html"
    )

    # Save to database
    detector.save_drift_to_database(drift_results, conn)

    conn.close()
```

### Add Database Table for Drift Metrics

```sql
-- Add to infrastructure/postgres/schema.sql

CREATE TABLE IF NOT EXISTS data_drift_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    dataset_drift_detected BOOLEAN NOT NULL,
    drift_share FLOAT NOT NULL,
    num_drifted_features INTEGER NOT NULL,
    drifted_features JSONB,
    drift_details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_drift_timestamp ON data_drift_metrics(timestamp DESC);
```

### Airflow DAG for Drift Detection

```python
# airflow/dags/drift_detection_dag.py

"""
DAG: Data Drift Detection
Schedule: Daily
Purpose: Monitor feature distributions for drift
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import pandas as pd
import sys
sys.path.append('/opt/airflow/src')
from monitoring.data_drift_detector import DataDriftDetector

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=10)
}

dag = DAG(
    'drift_detection',
    default_args=default_args,
    description='Monitor data drift daily',
    schedule_interval='0 3 * * *',  # Daily at 3 AM (after model training)
    catchup=False,
    tags=['monitoring', 'data-quality']
)

def run_drift_detection(**context):
    """Run drift detection and save results"""

    postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
    conn = postgres_hook.get_conn()

    # Load reference data (first month of training data)
    query_reference = """
    SELECT
        feature_json->>'hour_of_day' as hour_of_day,
        feature_json->>'day_of_week' as day_of_week,
        feature_json->>'is_weekend' as is_weekend,
        feature_json->>'bikes_lag_1h' as bikes_lag_1h,
        feature_json->>'bikes_lag_24h' as bikes_lag_24h,
        feature_json->>'bikes_rolling_mean_3h' as bikes_rolling_mean_3h,
        feature_json->>'temperature' as temperature,
        feature_json->>'humidity' as humidity
    FROM features
    WHERE timestamp BETWEEN '2024-01-01' AND '2024-01-31'
    LIMIT 10000
    """

    reference_df = pd.read_sql_query(query_reference, conn)

    # Convert to numeric
    for col in reference_df.columns:
        reference_df[col] = pd.to_numeric(reference_df[col], errors='coerce')

    # Load current data (last 7 days)
    query_current = """
    SELECT
        feature_json->>'hour_of_day' as hour_of_day,
        feature_json->>'day_of_week' as day_of_week,
        feature_json->>'is_weekend' as is_weekend,
        feature_json->>'bikes_lag_1h' as bikes_lag_1h,
        feature_json->>'bikes_lag_24h' as bikes_lag_24h,
        feature_json->>'bikes_rolling_mean_3h' as bikes_rolling_mean_3h,
        feature_json->>'temperature' as temperature,
        feature_json->>'humidity' as humidity
    FROM features
    WHERE timestamp >= NOW() - INTERVAL '7 days'
    LIMIT 10000
    """

    current_df = pd.read_sql_query(query_current, conn)

    # Convert to numeric
    for col in current_df.columns:
        current_df[col] = pd.to_numeric(current_df[col], errors='coerce')

    # Detect drift
    detector = DataDriftDetector(reference_data=reference_df)

    feature_cols = list(reference_df.columns)

    drift_results = detector.detect_drift(
        current_data=current_df,
        feature_columns=feature_cols,
        drift_threshold=0.5
    )

    # Save to database
    detector.save_drift_to_database(drift_results, conn)

    # Generate HTML report
    detector.generate_html_report(
        current_data=current_df,
        feature_columns=feature_cols,
        output_path="/opt/airflow/reports/drift_report.html"
    )

    conn.close()

    # Alert if drift detected
    if drift_results['dataset_drift_detected']:
        # Send alert (Slack, email, etc.)
        logging.warning(f"🚨 DATA DRIFT ALERT: {drift_results['num_drifted_features']} features drifted")

task_drift_detection = PythonOperator(
    task_id='detect_drift',
    python_callable=run_drift_detection,
    dag=dag
)
```

---

## Step 2: Model Performance Tracking

### `src/monitoring/model_performance_tracker.py`

```python
"""
Track model performance metrics over time
"""

import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from datetime import datetime
import logging
from typing import Dict

class ModelPerformanceTracker:
    def __init__(self, db_connection):
        self.conn = db_connection
        self.logger = logging.getLogger(__name__)

    def calculate_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> Dict:
        """
        Calculate regression metrics

        Args:
            y_true: Actual values
            y_pred: Predicted values

        Returns:
            Dict of metrics
        """
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-10))) * 100
        r2 = r2_score(y_true, y_pred)

        # Custom metric: Peak hour accuracy (7-9 AM, 5-7 PM)
        # This would require timestamp info - simplified here
        peak_hour_mape = mape  # Placeholder

        metrics = {
            'rmse': float(rmse),
            'mae': float(mae),
            'mape': float(mape),
            'r2_score': float(r2),
            'peak_hour_mape': float(peak_hour_mape)
        }

        return metrics

    def log_metrics(
        self,
        model_name: str,
        model_version: str,
        metrics: Dict
    ):
        """
        Save metrics to database

        Args:
            model_name: Name of model
            model_version: Version/run ID
            metrics: Metric dictionary
        """
        cursor = self.conn.cursor()

        insert_query = """
        INSERT INTO model_performance (
            model_name,
            model_version,
            evaluation_date,
            rmse,
            mae,
            mape,
            r2_score,
            data_drift_score
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(insert_query, (
            model_name,
            model_version,
            datetime.now(),
            metrics['rmse'],
            metrics['mae'],
            metrics['mape'],
            metrics['r2_score'],
            0.0  # Will be filled by drift detection
        ))

        self.conn.commit()
        cursor.close()

        self.logger.info(f"Logged metrics for {model_name} v{model_version}: RMSE={metrics['rmse']:.3f}")

    def get_performance_trend(
        self,
        model_name: str,
        days: int = 30
    ) -> pd.DataFrame:
        """
        Get performance metrics over time

        Args:
            model_name: Model name
            days: Number of days to retrieve

        Returns:
            DataFrame with metrics over time
        """
        query = """
        SELECT
            evaluation_date,
            model_version,
            rmse,
            mae,
            mape,
            r2_score
        FROM model_performance
        WHERE model_name = %s
          AND evaluation_date >= NOW() - INTERVAL '%s days'
        ORDER BY evaluation_date DESC
        """

        df = pd.read_sql_query(query, self.conn, params=(model_name, days))
        return df

    def check_degradation(
        self,
        model_name: str,
        rmse_threshold: float = 1.0,
        lookback_days: int = 7
    ) -> bool:
        """
        Check if model has degraded beyond threshold

        Args:
            model_name: Model to check
            rmse_threshold: RMSE threshold
            lookback_days: Days to average over

        Returns:
            True if degraded, False otherwise
        """
        df = self.get_performance_trend(model_name, days=lookback_days)

        if df.empty:
            return False

        avg_rmse = df['rmse'].mean()

        if avg_rmse > rmse_threshold:
            self.logger.warning(
                f"⚠️ MODEL DEGRADATION: {model_name} avg RMSE ({avg_rmse:.3f}) exceeds threshold ({rmse_threshold})"
            )
            return True

        return False
```

### Integration with Prediction API

Update `src/serving/predictor.py` to log predictions:

```python
class BikeDedemandPredictor:
    def __init__(self, model_loader, db_connection):
        self.model_loader = model_loader
        self.db_connection = db_connection

    def predict(self, station_id: str, timestamp: Optional[datetime] = None) -> Dict:
        # ... existing prediction code ...

        # Log prediction for monitoring
        self._log_prediction(
            station_id=station_id,
            timestamp=prediction_time,
            predicted_demand=prediction,
            actual_demand=None  # Will be filled later when actual is known
        )

        return result

    def _log_prediction(
        self,
        station_id: str,
        timestamp: datetime,
        predicted_demand: float,
        actual_demand: Optional[float] = None
    ):
        """Log prediction to database for monitoring"""

        cursor = self.db_connection.cursor()

        insert_query = """
        INSERT INTO predictions (
            station_id,
            prediction_timestamp,
            predicted_demand,
            actual_demand,
            model_version,
            model_name
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (station_id, prediction_timestamp) DO UPDATE SET
            predicted_demand = EXCLUDED.predicted_demand,
            model_version = EXCLUDED.model_version,
            model_name = EXCLUDED.model_name
        """

        cursor.execute(insert_query, (
            station_id,
            timestamp,
            predicted_demand,
            actual_demand,
            self.model_loader.model_version,
            self.model_loader.model_name
        ))

        self.db_connection.commit()
        cursor.close()
```

### Backfill Actual Values

Create a periodic job to update predictions with actual observed values:

```python
# airflow/dags/backfill_actuals_dag.py

"""
DAG: Backfill Actual Values
Schedule: Hourly
Purpose: Update predictions with actual observed demand
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2024, 1, 1),
    'retries': 2
}

dag = DAG(
    'backfill_actuals',
    default_args=default_args,
    description='Match predictions with actual values',
    schedule_interval='0 * * * *',  # Hourly
    catchup=False,
    tags=['monitoring']
)

def backfill_actuals(**context):
    """
    Join predictions with actual bike counts
    """
    postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
    conn = postgres_hook.get_conn()
    cursor = conn.cursor()

    # Update predictions with actual values
    update_query = """
    UPDATE predictions p
    SET actual_demand = bss.bikes_available
    FROM bike_station_status bss
    WHERE p.station_id = bss.station_id
      AND p.prediction_timestamp = bss.timestamp
      AND p.actual_demand IS NULL
      AND p.prediction_timestamp >= NOW() - INTERVAL '24 hours'
    """

    cursor.execute(update_query)
    rows_updated = cursor.rowcount
    conn.commit()

    logging.info(f"Updated {rows_updated} predictions with actual values")

    cursor.close()
    conn.close()

task_backfill = PythonOperator(
    task_id='backfill_actuals',
    python_callable=backfill_actuals,
    dag=dag
)
```

---

## Step 3: System Monitoring with Prometheus

### Why Prometheus?

**Decision**: Prometheus vs. Datadog vs. New Relic

**Why Prometheus Won**:
- **Open Source**: Free, self-hosted
- **Pull Model**: Scrapes metrics from endpoints
- **Time-Series Database**: Optimized for metrics storage
- **PromQL**: Powerful query language
- **Grafana Integration**: Beautiful dashboards

### FastAPI Prometheus Integration

Already implemented in `src/serving/api/main.py`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(...)

# Automatically expose /metrics endpoint
Instrumentator().instrument(app).expose(app)
```

This provides:
- `http_request_duration_seconds` - Request latency histogram
- `http_requests_total` - Total requests by method, path, status
- `http_request_size_bytes` - Request body size
- `http_response_size_bytes` - Response body size

### Custom Metrics

Add custom metrics for business logic:

```python
# src/serving/api/main.py

from prometheus_client import Counter, Histogram, Gauge

# Custom metrics
prediction_counter = Counter(
    'bike_demand_predictions_total',
    'Total number of predictions made',
    ['station_id', 'model_version']
)

prediction_latency = Histogram(
    'bike_demand_prediction_duration_seconds',
    'Time to generate prediction',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

active_stations = Gauge(
    'bike_demand_active_stations',
    'Number of active bike stations'
)

# In prediction endpoint
@router.post("/", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    with prediction_latency.time():
        predictor = get_predictor()
        result = predictor.predict(
            station_id=request.station_id,
            timestamp=request.timestamp
        )

    prediction_counter.labels(
        station_id=request.station_id,
        model_version=result['model_version']
    ).inc()

    return result
```

### Prometheus Configuration

Create `infrastructure/monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'bike-demand-api'
    static_configs:
      - targets: ['api:8000']

  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'airflow'
    static_configs:
      - targets: ['airflow-webserver:8080']
```

### Docker Compose for Prometheus

Add to `infrastructure/docker-compose.yml`:

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - bike-demand-network

  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    environment:
      DATA_SOURCE_NAME: "postgresql://postgres:postgres@postgres:5432/bike_demand_db?sslmode=disable"
    ports:
      - "9187:9187"
    networks:
      - bike-demand-network
    depends_on:
      - postgres

volumes:
  prometheus-data:
```

---

## Step 4: Grafana Dashboards

### Setup Grafana

Add to `infrastructure/docker-compose.yml`:

```yaml
services:
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    networks:
      - bike-demand-network
    depends_on:
      - prometheus

volumes:
  grafana-data:
```

### Grafana Data Source

Create `infrastructure/monitoring/grafana/datasources/prometheus.yml`:

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

### Dashboard JSON

Create `infrastructure/monitoring/grafana/dashboards/bike-demand-monitoring.json`:

```json
{
  "dashboard": {
    "title": "Bike Demand Forecasting - System Monitoring",
    "panels": [
      {
        "id": 1,
        "title": "API Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total{job='bike-demand-api'}[5m])"
          }
        ],
        "type": "graph"
      },
      {
        "id": 2,
        "title": "API Latency (p50, p95, p99)",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "p50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "p95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "p99"
          }
        ],
        "type": "graph"
      },
      {
        "id": 3,
        "title": "Prediction Count (Last Hour)",
        "targets": [
          {
            "expr": "sum(increase(bike_demand_predictions_total[1h]))"
          }
        ],
        "type": "stat"
      },
      {
        "id": 4,
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~'5..'}[5m])"
          }
        ],
        "type": "graph"
      }
    ]
  }
}
```

### Access Grafana

1. Start services: `docker-compose up -d grafana`
2. Open `http://localhost:3000`
3. Login: `admin` / `admin`
4. Navigate to **Dashboards** → **Bike Demand Forecasting**

---

## Step 5: Alerting

### Prometheus Alert Rules

Create `infrastructure/monitoring/alert_rules.yml`:

```yaml
groups:
  - name: bike_demand_alerts
    interval: 30s
    rules:
      # High API latency
      - alert: HighAPILatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API latency p95 > 1 second"
          description: "API is responding slowly (p95: {{ $value }}s)"

      # High error rate
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "API error rate > 5%"
          description: "Error rate: {{ $value | humanizePercentage }}"

      # Model degradation
      - alert: ModelDegradation
        expr: avg_over_time(model_rmse[24h]) > 1.0
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Model RMSE exceeds threshold"
          description: "24h avg RMSE: {{ $value }}"

      # Data pipeline delay
      - alert: DataPipelineDelay
        expr: (time() - max(data_freshness_timestamp)) > 3600
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Data pipeline stalled"
          description: "No new data for {{ $value | humanizeDuration }}"
```

### Slack Alerting

Install Alertmanager:

```yaml
# docker-compose.yml

services:
  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
    networks:
      - bike-demand-network
```

Configure Slack webhook in `infrastructure/monitoring/alertmanager.yml`:

```yaml
global:
  slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

route:
  receiver: 'slack-notifications'
  group_by: ['alertname']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'slack-notifications'
    slack_configs:
      - channel: '#ml-alerts'
        title: '🚨 {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

---

## Testing Monitoring

### 1. Generate Traffic

```bash
# Stress test API
for i in {1..1000}; do
  curl -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{"station_id": "66dbefca-0aca-11e7-82f6-3863bb44ef7c"}' &
done
```

### 2. Check Prometheus Metrics

Open `http://localhost:9090`

Query: `rate(http_requests_total[5m])`

### 3. View Grafana Dashboard

Open `http://localhost:3000` → Dashboards → Bike Demand Monitoring

### 4. Trigger Data Drift

Manually modify feature distribution and run drift detection DAG

---

## Interview Talking Points

1. **"I implemented multi-layer monitoring: data drift with Evidently AI, model performance tracking in PostgreSQL, and system metrics with Prometheus"**

2. **"I built automated drift detection using Kolmogorov-Smirnov tests - the system alerts when >50% of features drift beyond threshold"**

3. **"I integrated Prometheus with FastAPI to track API latency (p50/p95/p99), throughput, and error rates in real-time"**

4. **"The system logs all predictions and backfills actual values hourly to calculate real-world RMSE/MAE for continuous monitoring"**

5. **"I set up Grafana dashboards and Alertmanager to send Slack notifications when model RMSE exceeds 1.0 or API latency spikes"**

---

## Summary

You've implemented production-grade monitoring:

✅ **Data Drift Detection** - Evidently AI with statistical tests
✅ **Model Performance Tracking** - RMSE/MAE/MAPE over time
✅ **API Metrics** - Prometheus for latency, throughput, errors
✅ **System Dashboards** - Grafana visualizations
✅ **Automated Alerting** - Slack notifications for degradation
✅ **Prediction Logging** - Track predictions vs actuals
✅ **Drift Reports** - Beautiful HTML reports for analysis

**Next Chapter**: [Chapter 10: CI/CD Pipeline](10-cicd.md) - Automate testing, Docker builds, and deployments with GitHub Actions.