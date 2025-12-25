"""
Demand Forecast Page
Real-time predictions and multi-hour forecasts
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Demand Forecast",
    page_icon="🔮",
    layout="wide"
)

# API Configuration
API_URL = st.secrets.get("API_URL", "http://localhost:8000")

st.title("🔮 Bike Demand Forecast")
st.markdown("Real-time predictions and multi-hour forecasts for bike station demand")

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
tab1, tab2, tab3 = st.tabs(["📍 Single Station Forecast", "🔄 Batch Predictions", "📈 Multi-Station Comparison"])

# Tab 1: Single Station Forecast
with tab1:
    st.header("Single Station Demand Forecast")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Configuration")

        # Station ID input
        station_id = st.text_input(
            "Station ID",
            value="station_1",
            help="Enter the bike station ID"
        )

        # Forecast horizon
        hours_ahead = st.slider(
            "Forecast Horizon (hours)",
            min_value=1,
            max_value=168,
            value=24,
            help="Number of hours to forecast ahead"
        )

        # Weather override (optional)
        use_custom_weather = st.checkbox("Use Custom Weather Data")

        weather_data = None
        if use_custom_weather:
            st.subheader("Weather Conditions")

            temperature = st.slider("Temperature (°C)", -20, 45, 20)
            humidity = st.slider("Humidity (%)", 0, 100, 65)
            wind_speed = st.slider("Wind Speed (m/s)", 0.0, 20.0, 5.0, 0.5)
            weather_condition = st.selectbox(
                "Weather Condition",
                ["Clear", "Clouds", "Rain", "Snow", "Storm"]
            )

            weather_data = {
                "temperature": temperature,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "weather_condition": weather_condition
            }

        # Generate forecast button
        if st.button("🔮 Generate Forecast", type="primary"):
            with st.spinner(f"Generating {hours_ahead}-hour forecast..."):
                try:
                    # Make API request
                    response = requests.get(
                        f"{API_URL}/predict/station/{station_id}/forecast",
                        params={"hours_ahead": hours_ahead},
                        timeout=30
                    )

                    if response.status_code == 200:
                        forecast_data = response.json()
                        st.session_state['forecast_data'] = forecast_data
                        st.session_state['station_id'] = station_id
                        st.success(f"✅ Forecast generated for {station_id}")
                    else:
                        st.error(f"❌ Forecast failed: {response.text}")

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    with col2:
        st.subheader("Forecast Results")

        # Display forecast if available
        if 'forecast_data' in st.session_state:
            forecast_data = st.session_state['forecast_data']

            # Convert to DataFrame
            df = pd.DataFrame(forecast_data['forecasts'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['lower'] = df['confidence_interval'].apply(lambda x: x['lower'])
            df['upper'] = df['confidence_interval'].apply(lambda x: x['upper'])

            # Summary metrics
            metric_col1, metric_col2, metric_col3 = st.columns(3)

            with metric_col1:
                avg_demand = df['predicted_demand'].mean()
                st.metric("Average Demand", f"{avg_demand:.1f} bikes")

            with metric_col2:
                peak_demand = df['predicted_demand'].max()
                peak_time = df.loc[df['predicted_demand'].idxmax(), 'timestamp']
                st.metric(
                    "Peak Demand",
                    f"{peak_demand:.1f} bikes",
                    delta=f"at {peak_time.strftime('%H:%M')}"
                )

            with metric_col3:
                min_demand = df['predicted_demand'].min()
                low_time = df.loc[df['predicted_demand'].idxmin(), 'timestamp']
                st.metric(
                    "Minimum Demand",
                    f"{min_demand:.1f} bikes",
                    delta=f"at {low_time.strftime('%H:%M')}"
                )

            # Plot forecast
            fig = go.Figure()

            # Predicted demand
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['predicted_demand'],
                mode='lines+markers',
                name='Predicted Demand',
                line=dict(color='#1E88E5', width=3),
                marker=dict(size=6)
            ))

            # Confidence interval
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['upper'],
                mode='lines',
                name='Upper Bound',
                line=dict(width=0),
                showlegend=False
            ))

            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['lower'],
                mode='lines',
                name='Confidence Interval (95%)',
                line=dict(width=0),
                fillcolor='rgba(30, 136, 229, 0.2)',
                fill='tonexty'
            ))

            fig.update_layout(
                title=f"Demand Forecast for {station_id}",
                xaxis_title="Time",
                yaxis_title="Bikes Available",
                hovermode='x unified',
                height=500,
                template='plotly_white'
            )

            st.plotly_chart(fig, use_container_width=True)

            # Data table
            with st.expander("📊 View Detailed Forecast Data"):
                display_df = df[['timestamp', 'hour_ahead', 'predicted_demand', 'lower', 'upper']].copy()
                display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
                display_df.columns = ['Time', 'Hour Ahead', 'Predicted', 'Lower (95%)', 'Upper (95%)']
                st.dataframe(display_df, use_container_width=True)

            # Download button
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Forecast CSV",
                data=csv,
                file_name=f"forecast_{station_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )

        else:
            st.info("👆 Configure settings and click 'Generate Forecast' to see predictions")

# Tab 2: Batch Predictions
with tab2:
    st.header("Batch Station Predictions")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Configuration")

        # Station IDs
        station_ids_input = st.text_area(
            "Station IDs (one per line)",
            value="station_1\nstation_2\nstation_3",
            height=150,
            help="Enter station IDs, one per line"
        )

        # Prediction time
        prediction_hours_ahead = st.slider(
            "Hours Ahead",
            min_value=1,
            max_value=24,
            value=1,
            help="Predict demand N hours from now"
        )

        if st.button("🔄 Predict Batch", type="primary"):
            station_ids = [s.strip() for s in station_ids_input.split('\n') if s.strip()]

            if len(station_ids) > 100:
                st.error("❌ Maximum 100 stations allowed")
            else:
                with st.spinner(f"Predicting for {len(station_ids)} stations..."):
                    try:
                        # Prepare batch request
                        prediction_time = datetime.utcnow() + timedelta(hours=prediction_hours_ahead)

                        payload = {
                            "predictions": [
                                {
                                    "station_id": station_id,
                                    "timestamp": prediction_time.isoformat()
                                }
                                for station_id in station_ids
                            ]
                        }

                        # Make API request
                        response = requests.post(
                            f"{API_URL}/predict/batch",
                            json=payload,
                            timeout=60
                        )

                        if response.status_code == 200:
                            batch_data = response.json()
                            st.session_state['batch_data'] = batch_data
                            st.success(f"✅ Predictions generated for {batch_data['successful']} stations")

                            if batch_data['failed'] > 0:
                                st.warning(f"⚠️ {batch_data['failed']} predictions failed")
                        else:
                            st.error(f"❌ Batch prediction failed: {response.text}")

                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

    with col2:
        st.subheader("Prediction Results")

        if 'batch_data' in st.session_state:
            batch_data = st.session_state['batch_data']

            # Summary
            st.metric("Successful Predictions", f"{batch_data['successful']}/{batch_data['total_predictions']}")

            # Convert to DataFrame
            if batch_data['predictions']:
                predictions_df = pd.DataFrame(batch_data['predictions'])

                # Bar chart
                fig = px.bar(
                    predictions_df,
                    x='station_id',
                    y='predicted_demand',
                    title='Predicted Demand by Station',
                    labels={'predicted_demand': 'Predicted Bikes', 'station_id': 'Station'},
                    color='predicted_demand',
                    color_continuous_scale='Blues'
                )

                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

                # Data table
                display_df = predictions_df[['station_id', 'predicted_demand']].copy()
                display_df.columns = ['Station ID', 'Predicted Demand']
                display_df['Predicted Demand'] = display_df['Predicted Demand'].round(2)

                st.dataframe(display_df, use_container_width=True)

                # Download
                csv = display_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Predictions CSV",
                    data=csv,
                    file_name=f"batch_predictions_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No predictions available")
        else:
            st.info("👆 Configure settings and click 'Predict Batch' to see results")

# Tab 3: Multi-Station Comparison
with tab3:
    st.header("Multi-Station Forecast Comparison")

    st.info("🚧 Feature coming soon: Compare forecast trends across multiple stations")

    # Placeholder for future implementation
    st.markdown("""
    **Planned Features:**
    - Side-by-side forecast comparison
    - Heatmap of demand across stations
    - Correlation analysis between stations
    - Peak hours comparison
    """)
