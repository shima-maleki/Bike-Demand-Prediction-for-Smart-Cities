# Bike Demand Prediction Dashboard

Interactive Streamlit dashboard for monitoring and visualizing bike demand forecasts.

## 🚀 Quick Start

### Prerequisites

1. API server running on http://localhost:8000
2. PostgreSQL database with data
3. Python 3.11+

### Installation

```bash
# Install dependencies (from project root)
uv sync

# Or install Streamlit manually
pip install streamlit plotly pandas requests
```

### Configuration

1. Copy the secrets template:
```bash
cd dashboard/.streamlit
cp secrets.toml.example secrets.toml
```

2. Update `secrets.toml` with your API URL:
```toml
API_URL = "http://localhost:8000"
```

### Run the Dashboard

```bash
# From project root
streamlit run dashboard/app.py

# Or from dashboard directory
cd dashboard
streamlit run app.py
```

The dashboard will open automatically in your browser at http://localhost:8501

## 📊 Features

### 🔮 Demand Forecast
- **Single Station Forecast**: Generate multi-hour forecasts for individual stations
- **Batch Predictions**: Predict demand for multiple stations simultaneously
- **Custom Weather**: Override weather conditions for scenario testing
- **Interactive Charts**: Plotly-powered visualizations with confidence intervals
- **Data Export**: Download forecasts as CSV

### 📊 Model Performance
- **Current Model Metrics**: RMSE, MAE, MAPE, R² scores
- **Performance History**: Track model performance over time
- **Visual Comparisons**: Charts and gauges for easy interpretation
- **MLflow Integration**: Direct links to experiment tracking

### ✅ Data Quality
- **Pipeline Overview**: Monitor data collection and processing
- **Quality Checks**: View automated data quality validations
- **Data Freshness**: Track when data was last updated
- **Collection Trends**: Visualize data ingestion over time

### 💓 System Health
- **Component Status**: Monitor API, model, database, MLflow
- **Service Monitoring**: Check status of all Docker services
- **Health Metrics**: Prometheus metrics visualization
- **Quick Actions**: Reload models, run health checks

## 🎨 Pages

### Main Dashboard (app.py)
- Welcome screen
- System status overview
- Quick model metrics
- Navigation to detailed pages

### Page 1: 🔮 Demand Forecast
- Single station forecasting
- Batch predictions
- Multi-station comparison

### Page 2: 📊 Model Performance
- Current model metrics
- Performance history
- Model comparison

### Page 3: ✅ Data Quality
- Data pipeline overview
- Quality check results
- Freshness monitoring

### Page 4: 💓 System Health
- Component health status
- System metrics (Prometheus)
- Service status checks

## 🐳 Docker Deployment

### Build Image

```bash
docker build -f docker/dashboard/Dockerfile -t bike-demand-dashboard:latest .
```

### Run Container

```bash
docker run -d \
  --name bike-demand-dashboard \
  -p 8501:8501 \
  -e API_URL="http://api:8000" \
  bike-demand-dashboard:latest
```

### Using Docker Compose

The dashboard is included in the main `docker-compose.yml`:

```bash
docker-compose up dashboard
```

## ⚙️ Configuration

### Theme Configuration (.streamlit/config.toml)

```toml
[theme]
primaryColor = "#1E88E5"  # Blue
backgroundColor = "#FFFFFF"  # White
secondaryBackgroundColor = "#F0F2F6"  # Light gray
textColor = "#262730"  # Dark gray
font = "sans serif"

[server]
port = 8501
enableCORS = false
```

### Secrets (.streamlit/secrets.toml)

```toml
# API endpoint
API_URL = "http://localhost:8000"

# Add other secrets as needed
# DATABASE_URL = "..."
```

**Important**: `secrets.toml` is git-ignored for security

## 📸 Screenshots

### Demand Forecast
![Forecast Page](screenshots/forecast.png)
*Generate multi-hour forecasts with confidence intervals*

### Model Performance
![Performance Page](screenshots/performance.png)
*Monitor model metrics and evaluation results*

### Data Quality
![Data Quality Page](screenshots/data_quality.png)
*Track data pipeline health and freshness*

### System Health
![System Health Page](screenshots/system_health.png)
*Monitor all system components and services*

## 🔧 Development

### Project Structure

```
dashboard/
├── app.py                          # Main dashboard
├── pages/
│   ├── 1_🔮_Demand_Forecast.py    # Forecasting page
│   ├── 2_📊_Model_Performance.py  # Performance metrics
│   ├── 3_✅_Data_Quality.py       # Data monitoring
│   └── 4_💓_System_Health.py      # System status
├── .streamlit/
│   ├── config.toml                 # Theme and server config
│   └── secrets.toml.example        # Secrets template
└── README.md
```

### Adding New Pages

Streamlit automatically discovers pages in the `pages/` directory. To add a new page:

1. Create a new file in `pages/` with format: `N_emoji_Page_Name.py`
2. The file will appear in the sidebar navigation
3. Use st.set_page_config() at the top of each page

### Customizing Charts

The dashboard uses Plotly for interactive visualizations:

```python
import plotly.express as px
import plotly.graph_objects as go

# Line chart
fig = px.line(df, x='date', y='value', title='My Chart')
st.plotly_chart(fig, use_container_width=True)

# Gauge chart
fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=75,
    title={'text': "Health Score"}
))
st.plotly_chart(fig)
```

## 🚨 Troubleshooting

### Dashboard won't start

**Error**: `ModuleNotFoundError: No module named 'streamlit'`

**Solution**:
```bash
pip install streamlit plotly
```

### Cannot connect to API

**Error**: "❌ API is not available"

**Solutions**:
1. Ensure API is running: `python src/serving/api/main.py`
2. Check API_URL in secrets.toml
3. Verify API health: `curl http://localhost:8000/health`

### No data displayed

**Issue**: Charts are empty or show "No data available"

**Solutions**:
1. Run data collection DAG in Airflow
2. Wait for feature engineering DAG
3. Check database has records: `psql $DATABASE_URL`

### Slow performance

**Issue**: Dashboard is slow or laggy

**Solutions**:
1. Reduce forecast horizon (use fewer hours)
2. Enable caching with `@st.cache_data`
3. Limit batch prediction size
4. Use pagination for large tables

## 📚 API Integration

The dashboard integrates with the FastAPI backend:

```python
import requests

# Get forecast
response = requests.get(
    f"{API_URL}/predict/station/station_1/forecast",
    params={"hours_ahead": 24}
)
forecast = response.json()

# Make prediction
response = requests.post(
    f"{API_URL}/predict",
    json={
        "station_id": "station_1",
        "weather_data": {...}
    }
)
prediction = response.json()
```

## 🎯 Best Practices

1. **Error Handling**: Always wrap API calls in try-except
2. **Loading States**: Use `st.spinner()` for long operations
3. **Caching**: Cache expensive operations with `@st.cache_data`
4. **User Feedback**: Provide clear success/error messages
5. **Responsive Design**: Use columns for multi-column layouts

## 📖 Resources

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Plotly Documentation](https://plotly.com/python/)
- [API Documentation](http://localhost:8000/docs)

## 🤝 Contributing

To contribute to the dashboard:

1. Add new visualizations in existing pages
2. Create new pages for additional features
3. Improve error handling and user experience
4. Add unit tests for data processing logic

## 📄 License

MIT License - See root project LICENSE file

---

**Project**: Bike Demand Prediction for Smart Cities
**GitHub**: https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities
