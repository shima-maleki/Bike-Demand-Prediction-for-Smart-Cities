"""
System Health Page
Monitor system components, infrastructure, and service health
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import sys
from pathlib import Path
import os

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Page config
st.set_page_config(
    page_title="System Health",
    page_icon="💓",
    layout="wide"
)

# API Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.title("💓 System Health")
st.markdown("Monitor all system components, services, and infrastructure health")

# Auto-refresh toggle
auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)
if auto_refresh:
    import time
    time.sleep(30)
    st.rerun()

# Tabs
tab1, tab2, tab3 = st.tabs(["🏥 Component Health", "📊 System Metrics", "🔧 Service Status"])

# Tab 1: Component Health
with tab1:
    st.header("Component Health Status")

    # Fetch detailed health
    try:
        response = requests.get(f"{API_URL}/health/detailed", timeout=5)

        if response.status_code == 200:
            health_data = response.json()

            # Overall Status
            overall_status = health_data.get('status', 'unknown')

            col1, col2, col3 = st.columns([1, 2, 1])

            with col2:
                if overall_status == 'healthy':
                    st.success("## ✅ All Systems Operational")
                elif overall_status == 'degraded':
                    st.warning("## ⚠️ System Degraded")
                else:
                    st.error("## ❌ System Unhealthy")

            st.markdown("---")

            # Component Status Cards
            components = health_data.get('components', {})

            if components:
                # API Component
                if 'api' in components:
                    api_comp = components['api']

                    with st.expander("🌐 API Service", expanded=True):
                        status = api_comp.get('status', 'unknown')

                        comp_col1, comp_col2 = st.columns(2)

                        with comp_col1:
                            if status == 'healthy':
                                st.success(f"**Status:** {status.upper()}")
                            else:
                                st.error(f"**Status:** {status.upper()}")

                        with comp_col2:
                            st.info(f"**Version:** {api_comp.get('version', 'N/A')}")

                        st.write(f"**Timestamp:** {api_comp.get('timestamp', 'N/A')}")

                # Model Component
                if 'model' in components:
                    model_comp = components['model']

                    with st.expander("🤖 ML Model", expanded=True):
                        status = model_comp.get('status', 'unknown')
                        loaded = model_comp.get('loaded', False)

                        comp_col1, comp_col2 = st.columns(2)

                        with comp_col1:
                            if status == 'healthy':
                                st.success(f"**Status:** {status.upper()}")
                            elif status == 'degraded':
                                st.warning(f"**Status:** {status.upper()}")
                            else:
                                st.error(f"**Status:** {status.upper()}")

                        with comp_col2:
                            if loaded:
                                st.success("**Loaded:** Yes")
                            else:
                                st.error("**Loaded:** No")

                        # Model Info
                        model_info = model_comp.get('info', {})
                        if model_info:
                            st.write(f"**Model:** {model_info.get('name', 'N/A')}")
                            st.write(f"**Version:** {model_info.get('version', 'N/A')}")
                            st.write(f"**Stage:** {model_info.get('stage', 'N/A')}")

                        # Error message
                        if 'error' in model_comp:
                            st.error(f"**Error:** {model_comp['error']}")

                # Database Component
                if 'database' in components:
                    db_comp = components['database']

                    with st.expander("🗄️ Database", expanded=True):
                        status = db_comp.get('status', 'unknown')
                        connected = db_comp.get('connected', False)

                        comp_col1, comp_col2 = st.columns(2)

                        with comp_col1:
                            if status == 'healthy':
                                st.success(f"**Status:** {status.upper()}")
                            else:
                                st.error(f"**Status:** {status.upper()}")

                        with comp_col2:
                            if connected:
                                st.success("**Connected:** Yes")
                            else:
                                st.error("**Connected:** No")

                        if 'error' in db_comp:
                            st.error(f"**Error:** {db_comp['error']}")

                # MLflow Component
                if 'mlflow' in components:
                    mlflow_comp = components['mlflow']

                    with st.expander("📊 MLflow", expanded=True):
                        status = mlflow_comp.get('status', 'unknown')
                        connected = mlflow_comp.get('connected', False)

                        comp_col1, comp_col2 = st.columns(2)

                        with comp_col1:
                            if status == 'healthy':
                                st.success(f"**Status:** {status.upper()}")
                            elif status == 'degraded':
                                st.warning(f"**Status:** {status.upper()}")
                            else:
                                st.error(f"**Status:** {status.upper()}")

                        with comp_col2:
                            if connected:
                                st.success("**Connected:** Yes")
                            else:
                                st.warning("**Connected:** No")

                        st.write(f"**Tracking URI:** {mlflow_comp.get('tracking_uri', 'N/A')}")

                        if 'error' in mlflow_comp:
                            st.warning(f"**Note:** {mlflow_comp['error']}")

            # Health Summary Visualization
            st.markdown("---")
            st.subheader("📊 Component Health Summary")

            # Create gauge chart for overall health
            health_scores = {
                'healthy': 100,
                'degraded': 50,
                'unhealthy': 0,
                'unknown': 25
            }

            component_statuses = [comp.get('status', 'unknown') for comp in components.values()]
            avg_health = sum(health_scores.get(status, 0) for status in component_statuses) / len(component_statuses) if component_statuses else 0

            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=avg_health,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Overall System Health"},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "#1E88E5"},
                    'steps': [
                        {'range': [0, 50], 'color': "#FFCDD2"},
                        {'range': [50, 80], 'color': "#FFF9C4"},
                        {'range': [80, 100], 'color': "#C8E6C9"}
                    ],
                    'threshold': {
                        'line': {'color': "green", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))

            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.error(f"Failed to fetch health status: {response.status_code}")

    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API. Is the API server running?")
        st.code("python src/serving/api/main.py", language="bash")

    except Exception as e:
        st.error(f"Error checking system health: {str(e)}")

# Tab 2: System Metrics
with tab2:
    st.header("System Metrics")

    # Fetch Prometheus metrics
    try:
        response = requests.get(f"{API_URL}/monitoring/metrics", timeout=5)

        if response.status_code == 200:
            metrics_text = response.text

            # Parse metrics (simple parsing)
            metrics_lines = [line for line in metrics_text.split('\n') if line and not line.startswith('#')]

            if metrics_lines:
                st.success(f"✅ Fetched {len(metrics_lines)} metrics")

                # Display metrics
                st.subheader("📊 Key Metrics")

                # Parse and display key metrics
                metrics_dict = {}
                for line in metrics_lines:
                    if ' ' in line:
                        parts = line.rsplit(' ', 1)
                        if len(parts) == 2:
                            metric_name = parts[0].split('{')[0]
                            try:
                                metric_value = float(parts[1])
                                metrics_dict[metric_name] = metric_value
                            except:
                                pass

                # Display in columns
                if metrics_dict:
                    metric_col1, metric_col2 = st.columns(2)

                    with metric_col1:
                        for metric, value in list(metrics_dict.items())[:len(metrics_dict)//2]:
                            st.metric(metric.replace('bike_demand_', '').replace('_', ' ').title(), f"{value:.2f}")

                    with metric_col2:
                        for metric, value in list(metrics_dict.items())[len(metrics_dict)//2:]:
                            st.metric(metric.replace('bike_demand_', '').replace('_', ' ').title(), f"{value:.2f}")

                # Raw metrics
                with st.expander("📄 View Raw Prometheus Metrics"):
                    st.code(metrics_text, language="text")

            else:
                st.info("No metrics available")

        else:
            st.warning(f"Could not fetch metrics: {response.status_code}")

    except Exception as e:
        st.warning(f"Could not load metrics: {str(e)}")

# Tab 3: Service Status
with tab3:
    st.header("Service Status")

    st.subheader("🐳 Docker Services")

    # Service status list
    services = [
        {
            'name': 'PostgreSQL',
            'port': 5432,
            'description': 'Database for storing bike station data, weather, and features',
            'health_check': 'psql connection'
        },
        {
            'name': 'MLflow',
            'port': 5000,
            'description': 'Experiment tracking and model registry',
            'health_check': 'HTTP GET /health'
        },
        {
            'name': 'FastAPI',
            'port': 8000,
            'description': 'Model serving API',
            'health_check': 'HTTP GET /health'
        },
        {
            'name': 'Airflow Webserver',
            'port': 8080,
            'description': 'Workflow orchestration UI',
            'health_check': 'HTTP GET /health'
        },
        {
            'name': 'Streamlit',
            'port': 8501,
            'description': 'Dashboard UI',
            'health_check': 'HTTP GET /'
        }
    ]

    for service in services:
        with st.expander(f"{service['name']} (Port {service['port']})", expanded=False):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.write(f"**Description:** {service['description']}")
                st.write(f"**Health Check:** {service['health_check']}")
                st.write(f"**Port:** {service['port']}")

            with col2:
                # Try to check if service is accessible (simple check)
                try:
                    if service['name'] == 'FastAPI':
                        resp = requests.get(f"http://localhost:{service['port']}/health", timeout=2)
                        if resp.status_code == 200:
                            st.success("✅ Online")
                        else:
                            st.warning("⚠️ Responding but unhealthy")
                    else:
                        st.info("ℹ️ Manual check required")
                except:
                    st.error("❌ Offline")

    st.markdown("---")

    # Quick links
    st.subheader("🔗 Quick Links")

    link_col1, link_col2 = st.columns(2)

    with link_col1:
        st.markdown("[🌐 API Documentation](http://localhost:8000/docs)")
        st.markdown("[📊 MLflow UI](http://localhost:5000)")
        st.markdown("[🔄 Airflow UI](http://localhost:8080)")

    with link_col2:
        st.markdown("[💓 API Health](http://localhost:8000/health/detailed)")
        st.markdown("[📈 Prometheus Metrics](http://localhost:8000/monitoring/metrics)")
        st.markdown("[📊 Current Model](http://localhost:8000/monitoring/models/current)")

# Actions
st.markdown("---")
st.subheader("⚡ Quick Actions")

action_col1, action_col2, action_col3 = st.columns(3)

with action_col1:
    if st.button("🔄 Refresh Status"):
        st.rerun()

with action_col2:
    if st.button("💓 Run Health Check"):
        with st.spinner("Running health checks..."):
            try:
                response = requests.get(f"{API_URL}/health/detailed")
                if response.status_code == 200:
                    st.json(response.json())
                else:
                    st.error("Health check failed")
            except:
                st.error("Could not connect to API")

with action_col3:
    if st.button("📊 View System Stats"):
        try:
            response = requests.get(f"{API_URL}/monitoring/stats")
            if response.status_code == 200:
                st.json(response.json())
        except:
            st.error("Could not fetch stats")

# Footer with last update time
st.markdown("---")
st.caption(f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
