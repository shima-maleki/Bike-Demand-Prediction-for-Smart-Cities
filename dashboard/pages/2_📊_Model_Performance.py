"""
Model Performance Page
Model metrics, evaluation, and comparison
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import sys
from pathlib import Path
import os

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Page config
st.set_page_config(
    page_title="Model Performance",
    page_icon="📊",
    layout="wide"
)

# API Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.title("📊 Model Performance")
st.markdown("Monitor model metrics, evaluation results, and performance over time")

# Check API health
try:
    health_check = requests.get(f"{API_URL}/health", timeout=2)
    api_healthy = health_check.status_code == 200
except:
    api_healthy = False

if not api_healthy:
    st.error("⚠️ API is not available. Please start the API server.")
    st.stop()

# Tabs
tab1, tab2, tab3 = st.tabs(["🎯 Current Model", "📈 Performance History", "🔬 Model Comparison"])

# Tab 1: Current Model
with tab1:
    st.header("Current Production Model")

    # Fetch current model info
    try:
        response = requests.get(f"{API_URL}/monitoring/models/current", timeout=5)

        if response.status_code == 200:
            model_data = response.json()
            model_info = model_data.get('model_info', {})
            metrics = model_data.get('metrics', {})

            # Model Info Section
            st.subheader("📋 Model Information")

            info_col1, info_col2, info_col3, info_col4 = st.columns(4)

            with info_col1:
                st.metric("Model Name", model_info.get('name', 'N/A'))

            with info_col2:
                st.metric("Version", model_info.get('version', 'N/A'))

            with info_col3:
                st.metric("Stage", model_info.get('stage', 'N/A'))

            with info_col4:
                loaded_at = model_info.get('loaded_at', 'N/A')
                if loaded_at != 'N/A':
                    loaded_time = datetime.fromisoformat(loaded_at.replace('Z', '+00:00'))
                    st.metric("Loaded", loaded_time.strftime('%H:%M:%S'))
                else:
                    st.metric("Loaded", "N/A")

            st.markdown("---")

            # Performance Metrics Section
            if metrics:
                st.subheader("📊 Performance Metrics")

                # Test Set Metrics
                st.markdown("#### Test Set Performance")

                test_col1, test_col2, test_col3, test_col4 = st.columns(4)

                with test_col1:
                    test_rmse = metrics.get('test_rmse')
                    if test_rmse is not None:
                        st.metric(
                            "RMSE",
                            f"{test_rmse:.2f}",
                            help="Root Mean Squared Error on test set"
                        )
                        # Quality indicator
                        if test_rmse < 5:
                            st.success("✅ Excellent")
                        elif test_rmse < 10:
                            st.info("👍 Good")
                        else:
                            st.warning("⚠️ Needs Improvement")

                with test_col2:
                    test_mae = metrics.get('test_mae')
                    if test_mae is not None:
                        st.metric(
                            "MAE",
                            f"{test_mae:.2f}",
                            help="Mean Absolute Error on test set"
                        )

                with test_col3:
                    test_mape = metrics.get('test_mape')
                    if test_mape is not None:
                        st.metric(
                            "MAPE",
                            f"{test_mape:.2f}%",
                            help="Mean Absolute Percentage Error on test set"
                        )
                        if test_mape < 15:
                            st.success("✅ Excellent")
                        elif test_mape < 25:
                            st.info("👍 Good")
                        else:
                            st.warning("⚠️ Needs Improvement")

                with test_col4:
                    test_r2 = metrics.get('test_r2')
                    if test_r2 is not None:
                        st.metric(
                            "R² Score",
                            f"{test_r2:.4f}",
                            help="Coefficient of determination on test set"
                        )
                        if test_r2 > 0.8:
                            st.success("✅ Excellent")
                        elif test_r2 > 0.6:
                            st.info("👍 Good")
                        else:
                            st.warning("⚠️ Needs Improvement")

                # Validation Set Metrics
                st.markdown("#### Validation Set Performance")

                val_col1, val_col2, val_col3, val_col4 = st.columns(4)

                with val_col1:
                    val_rmse = metrics.get('val_rmse')
                    if val_rmse is not None:
                        st.metric("RMSE", f"{val_rmse:.2f}")

                with val_col2:
                    val_mae = metrics.get('val_mae')
                    if val_mae is not None:
                        st.metric("MAE", f"{val_mae:.2f}")

                with val_col3:
                    val_mape = metrics.get('val_mape')
                    if val_mape is not None:
                        st.metric("MAPE", f"{val_mape:.2f}%")

                with val_col4:
                    val_r2 = metrics.get('val_r2')
                    if val_r2 is not None:
                        st.metric("R² Score", f"{val_r2:.4f}")

                # Metrics Visualization
                st.markdown("---")
                st.subheader("📈 Metrics Visualization")

                viz_col1, viz_col2 = st.columns(2)

                with viz_col1:
                    # Error Metrics Comparison
                    error_metrics_df = pd.DataFrame({
                        'Metric': ['RMSE', 'MAE', 'MAPE'],
                        'Test': [
                            metrics.get('test_rmse', 0),
                            metrics.get('test_mae', 0),
                            metrics.get('test_mape', 0)
                        ],
                        'Validation': [
                            metrics.get('val_rmse', 0),
                            metrics.get('val_mae', 0),
                            metrics.get('val_mape', 0)
                        ]
                    })

                    fig_errors = go.Figure()

                    fig_errors.add_trace(go.Bar(
                        name='Test',
                        x=error_metrics_df['Metric'],
                        y=error_metrics_df['Test'],
                        marker_color='#1E88E5'
                    ))

                    fig_errors.add_trace(go.Bar(
                        name='Validation',
                        x=error_metrics_df['Metric'],
                        y=error_metrics_df['Validation'],
                        marker_color='#FFA726'
                    ))

                    fig_errors.update_layout(
                        title='Error Metrics Comparison',
                        barmode='group',
                        height=300,
                        template='plotly_white'
                    )

                    st.plotly_chart(fig_errors, use_container_width=True)

                with viz_col2:
                    # R² Score Gauge
                    test_r2_val = metrics.get('test_r2', 0)

                    fig_gauge = go.Figure(go.Indicator(
                        mode="gauge+number+delta",
                        value=test_r2_val,
                        domain={'x': [0, 1], 'y': [0, 1]},
                        title={'text': "Test R² Score"},
                        delta={'reference': 0.8},
                        gauge={
                            'axis': {'range': [0, 1]},
                            'bar': {'color': "#1E88E5"},
                            'steps': [
                                {'range': [0, 0.6], 'color': "#FFCDD2"},
                                {'range': [0.6, 0.8], 'color': "#FFF9C4"},
                                {'range': [0.8, 1], 'color': "#C8E6C9"}
                            ],
                            'threshold': {
                                'line': {'color': "red", 'width': 4},
                                'thickness': 0.75,
                                'value': 0.9
                            }
                        }
                    ))

                    fig_gauge.update_layout(height=300)
                    st.plotly_chart(fig_gauge, use_container_width=True)

            else:
                st.info("No metrics available for the current model")

            # Model Details
            with st.expander("🔍 Detailed Model Information"):
                st.json(model_info)

                if metrics:
                    st.markdown("**Performance Metrics:**")
                    st.json(metrics)

        else:
            st.error(f"Failed to fetch model information: {response.status_code}")

    except Exception as e:
        st.error(f"Error fetching model data: {str(e)}")

# Tab 2: Performance History
with tab2:
    st.header("Model Performance Over Time")

    # Fetch historical performance from database
    try:
        from src.config.database import get_db_context
        from sqlalchemy import select
        from src.data.models import ModelPerformance

        with get_db_context() as db:
            query = select(ModelPerformance).order_by(ModelPerformance.evaluation_date.desc()).limit(50)
            results = db.execute(query).fetchall()

            if results:
                # Convert to DataFrame
                history_data = []
                for row in results:
                    perf = row[0]
                    history_data.append({
                        'Date': perf.evaluation_date,
                        'Model': perf.model_name,
                        'Version': perf.model_version,
                        'RMSE': perf.rmse,
                        'MAE': perf.mae,
                        'MAPE': perf.mape,
                        'R²': perf.r2_score
                    })

                history_df = pd.DataFrame(history_data)
                history_df = history_df.sort_values('Date')

                # Metrics over time plot
                st.subheader("📈 RMSE Trend Over Time")

                fig_history = px.line(
                    history_df,
                    x='Date',
                    y='RMSE',
                    color='Model',
                    markers=True,
                    title='Model RMSE Over Time',
                    labels={'RMSE': 'RMSE (bikes)', 'Date': 'Evaluation Date'}
                )

                fig_history.update_layout(height=400, template='plotly_white')
                st.plotly_chart(fig_history, use_container_width=True)

                # MAPE trend
                st.subheader("📉 MAPE Trend Over Time")

                fig_mape = px.line(
                    history_df,
                    x='Date',
                    y='MAPE',
                    color='Model',
                    markers=True,
                    title='Model MAPE Over Time',
                    labels={'MAPE': 'MAPE (%)', 'Date': 'Evaluation Date'}
                )

                fig_mape.update_layout(height=400, template='plotly_white')
                st.plotly_chart(fig_mape, use_container_width=True)

                # Historical data table
                with st.expander("📊 View Historical Data"):
                    display_history = history_df.copy()
                    display_history['Date'] = display_history['Date'].dt.strftime('%Y-%m-%d %H:%M')
                    st.dataframe(display_history, use_container_width=True)

            else:
                st.info("No historical performance data available. Run model training to generate history.")

    except Exception as e:
        st.warning(f"Could not load performance history: {str(e)}")
        st.info("Historical performance tracking will be available after running model training.")

# Tab 3: Model Comparison
with tab3:
    st.header("Model Comparison")

    st.info("🚧 Feature coming soon: Compare multiple model versions")

    # Placeholder for future implementation
    st.markdown("""
    **Planned Features:**
    - Side-by-side model comparison
    - A/B test results
    - Champion vs challenger analysis
    - Model performance regression detection
    """)

# Actions
st.markdown("---")
st.subheader("⚡ Actions")

action_col1, action_col2 = st.columns(2)

with action_col1:
    if st.button("🔄 Refresh Metrics"):
        st.rerun()

with action_col2:
    if st.button("📊 View MLflow UI"):
        st.markdown("[Open MLflow UI](http://localhost:5000)")
