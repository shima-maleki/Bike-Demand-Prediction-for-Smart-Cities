"""
Bike Demand Prediction Dashboard
Main Streamlit application for monitoring and visualization
"""

import streamlit as st
import requests
from datetime import datetime
import sys
from pathlib import Path
import os

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import get_settings

settings = get_settings()

# Page config
st.set_page_config(
    page_title="Bike Demand Forecasting",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities',
        'Report a bug': 'https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities/issues',
        'About': "# Bike Demand Prediction Dashboard\n\nML-powered bike station demand forecasting for smart cities."
    }
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        margin: 1rem 0;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# API Configuration
API_URL = os.getenv("API_URL", st.secrets.get("API_URL", "http://localhost:8000"))


def check_api_health():
    """Check if API is healthy"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def get_api_status():
    """Get detailed API status"""
    try:
        response = requests.get(f"{API_URL}/health/detailed", timeout=2)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


# Sidebar
with st.sidebar:
    st.image("https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f6b4.png", width=80)
    st.title("🚴 Bike Demand Forecasting")

    st.markdown("---")

    # API Status
    st.subheader("System Status")

    if check_api_health():
        st.success("✅ API Online")

        # Get detailed status
        api_status = get_api_status()
        if api_status:
            components = api_status.get('components', {})

            # Model status
            model_status = components.get('model', {}).get('status', 'unknown')
            if model_status == 'healthy':
                st.success("✅ Model Loaded")
            elif model_status == 'degraded':
                st.warning("⚠️ Model Degraded")
            else:
                st.error("❌ Model Error")

            # Database status
            db_status = components.get('database', {}).get('status', 'unknown')
            if db_status == 'healthy':
                st.success("✅ Database Connected")
            else:
                st.error("❌ Database Error")
    else:
        st.error("❌ API Offline")
        st.warning("Please start the API server")
        st.code("python src/serving/api/main.py", language="bash")

    st.markdown("---")

    # Quick Links
    st.subheader("Quick Links")
    st.markdown(f"[API Documentation]({API_URL}/docs)")
    st.markdown(f"[API Health]({API_URL}/health)")
    st.markdown("[GitHub](https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities)")

    st.markdown("---")

    # About
    st.subheader("About")
    st.info("""
    **Bike Demand Prediction**

    ML-powered forecasting system for urban bike-sharing networks.

    - 🤖 XGBoost/LightGBM/CatBoost models
    - 📊 100+ engineered features
    - 🔄 Automated training pipeline
    - 📈 Real-time predictions
    """)

    st.markdown("---")
    st.caption(f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")


# Main Content
st.markdown("<div class='main-header'>🚴 Bike Demand Forecasting Dashboard</div>", unsafe_allow_html=True)

# Welcome message
st.markdown("""
Welcome to the **Bike Demand Prediction Dashboard**! This platform provides real-time forecasting
and monitoring for urban bike-sharing networks using advanced machine learning.

### 📋 Navigation

Use the sidebar to navigate between different sections:

- **🔮 Demand Forecast** - Real-time predictions and multi-hour forecasts
- **📊 Model Performance** - Model metrics and evaluation
- **✅ Data Quality** - Data pipeline monitoring
- **💓 System Health** - Infrastructure and component status

### 🚀 Getting Started

1. Ensure the API server is running (check status in sidebar)
2. Navigate to **Demand Forecast** to see predictions
3. View **Model Performance** to understand model accuracy
4. Monitor **Data Quality** for pipeline health
""")

st.markdown("---")

# Quick Overview Cards
if check_api_health():
    col1, col2, col3, col4 = st.columns(4)

    # Get current model info
    try:
        model_response = requests.get(f"{API_URL}/monitoring/models/current", timeout=2)
        if model_response.status_code == 200:
            model_data = model_response.json()
            model_info = model_data.get('model_info', {})
            metrics = model_data.get('metrics', {})

            with col1:
                st.metric(
                    label="Current Model",
                    value=model_info.get('name', 'Unknown')[:20],
                    delta=f"v{model_info.get('version', 'N/A')}"
                )

            with col2:
                test_rmse = metrics.get('test_rmse') if metrics else None
                st.metric(
                    label="Test RMSE",
                    value=f"{test_rmse:.2f}" if test_rmse else "N/A",
                    delta="bikes"
                )

            with col3:
                test_mape = metrics.get('test_mape') if metrics else None
                st.metric(
                    label="Test MAPE",
                    value=f"{test_mape:.2f}%" if test_mape else "N/A",
                    delta="error"
                )

            with col4:
                test_r2 = metrics.get('test_r2') if metrics else None
                st.metric(
                    label="Test R²",
                    value=f"{test_r2:.4f}" if test_r2 else "N/A",
                    delta="score"
                )
    except:
        st.warning("Could not fetch model information")

    st.markdown("---")

    # Quick Actions
    st.subheader("⚡ Quick Actions")

    action_col1, action_col2, action_col3 = st.columns(3)

    with action_col1:
        if st.button("🔄 Reload Model"):
            with st.spinner("Reloading model..."):
                try:
                    response = requests.post(f"{API_URL}/monitoring/models/reload")
                    if response.status_code == 200:
                        st.success("✅ Model reloaded successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to reload model")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    with action_col2:
        if st.button("📊 View API Docs"):
            st.markdown(f"[Open API Documentation]({API_URL}/docs)")

    with action_col3:
        if st.button("🔍 Check Health"):
            with st.spinner("Checking health..."):
                status = get_api_status()
                if status:
                    st.json(status)
                else:
                    st.error("Could not fetch health status")

else:
    st.error("⚠️ API is not available. Please start the API server to use the dashboard.")

    with st.expander("📖 How to start the API"):
        st.code("""
# Start the API server
python src/serving/api/main.py

# Or with uvicorn
uvicorn src.serving.api.main:app --reload --host 0.0.0.0 --port 8000
        """, language="bash")

st.markdown("---")

# Footer
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p><strong>Bike Demand Prediction for Smart Cities</strong></p>
    <p>Production-grade MLOps system with automated pipelines, experiment tracking, and model serving</p>
    <p>Built with: FastAPI • Streamlit • MLflow • Airflow • Docker • PostgreSQL</p>
</div>
""", unsafe_allow_html=True)
