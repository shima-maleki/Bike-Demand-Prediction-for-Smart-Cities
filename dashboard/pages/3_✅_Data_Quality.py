"""
Data Quality Page
Monitor data pipeline, quality checks, and data freshness
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Page config
st.set_page_config(
    page_title="Data Quality",
    page_icon="✅",
    layout="wide"
)

st.title("✅ Data Quality Monitoring")
st.markdown("Monitor data pipeline health, quality checks, and data freshness")

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Data Overview", "✅ Quality Checks", "🔄 Data Freshness"])

# Tab 1: Data Overview
with tab1:
    st.header("Data Pipeline Overview")

    try:
        from src.config.database import get_db_context
        from sqlalchemy import select, func
        from src.data.models import BikeStationStatus, WeatherData, Feature, BikeStation

        with get_db_context() as db:
            # Bike Stations
            station_count = db.query(func.count(BikeStation.station_id)).scalar()

            # Bike Station Status records
            status_count = db.query(func.count(BikeStationStatus.id)).scalar()
            latest_status = db.query(func.max(BikeStationStatus.timestamp)).scalar()

            # Weather records
            weather_count = db.query(func.count(WeatherData.id)).scalar()
            latest_weather = db.query(func.max(WeatherData.timestamp)).scalar()

            # Feature records
            feature_count = db.query(func.count(Feature.id)).scalar()
            latest_feature = db.query(func.max(Feature.timestamp)).scalar()

        # Display metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Bike Stations", f"{station_count:,}")

        with col2:
            st.metric("Status Records", f"{status_count:,}")
            if latest_status:
                time_diff = datetime.utcnow() - latest_status
                if time_diff.total_seconds() < 3600:  # 1 hour
                    st.success(f"✅ Fresh ({int(time_diff.total_seconds() / 60)} min ago)")
                else:
                    st.warning(f"⚠️ Stale ({int(time_diff.total_seconds() / 3600)} hours ago)")

        with col3:
            st.metric("Weather Records", f"{weather_count:,}")
            if latest_weather:
                time_diff = datetime.utcnow() - latest_weather
                if time_diff.total_seconds() < 3600:
                    st.success(f"✅ Fresh ({int(time_diff.total_seconds() / 60)} min ago)")
                else:
                    st.warning(f"⚠️ Stale ({int(time_diff.total_seconds() / 3600)} hours ago)")

        with col4:
            st.metric("Feature Records", f"{feature_count:,}")
            if latest_feature:
                time_diff = datetime.utcnow() - latest_feature
                if time_diff.total_seconds() < 7200:  # 2 hours
                    st.success(f"✅ Fresh ({int(time_diff.total_seconds() / 60)} min ago)")
                else:
                    st.warning(f"⚠️ Stale ({int(time_diff.total_seconds() / 3600)} hours ago)")

        st.markdown("---")

        # Data collection trend (last 7 days)
        st.subheader("📈 Data Collection Trend (Last 7 Days)")

        cutoff_date = datetime.utcnow() - timedelta(days=7)

        with get_db_context() as db:
            # Query records per day
            query = f"""
            SELECT
                DATE(timestamp) as date,
                COUNT(*) as count
            FROM bike_station_status
            WHERE timestamp >= '{cutoff_date.isoformat()}'
            GROUP BY DATE(timestamp)
            ORDER BY date
            """

            trend_df = pd.read_sql(query, db.connection())

            if len(trend_df) > 0:
                fig = px.bar(
                    trend_df,
                    x='date',
                    y='count',
                    title='Bike Status Records per Day',
                    labels={'count': 'Records', 'date': 'Date'},
                    color='count',
                    color_continuous_scale='Blues'
                )

                fig.update_layout(height=400, template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data available for the last 7 days")

        # Latest records preview
        st.subheader("🔍 Latest Records Preview")

        preview_col1, preview_col2 = st.columns(2)

        with preview_col1:
            st.markdown("**Latest Bike Station Statuses**")

            with get_db_context() as db:
                query = select(BikeStationStatus).order_by(
                    BikeStationStatus.timestamp.desc()
                ).limit(10)

                latest_statuses = pd.read_sql(query, db.connection())

                if len(latest_statuses) > 0:
                    display_statuses = latest_statuses[[
                        'station_id', 'timestamp', 'bikes_available', 'docks_available'
                    ]].copy()
                    display_statuses['timestamp'] = pd.to_datetime(
                        display_statuses['timestamp']
                    ).dt.strftime('%Y-%m-%d %H:%M')

                    st.dataframe(display_statuses, use_container_width=True)
                else:
                    st.info("No status records found")

        with preview_col2:
            st.markdown("**Latest Weather Data**")

            with get_db_context() as db:
                query = select(WeatherData).order_by(
                    WeatherData.timestamp.desc()
                ).limit(10)

                latest_weather = pd.read_sql(query, db.connection())

                if len(latest_weather) > 0:
                    display_weather = latest_weather[[
                        'timestamp', 'temperature', 'humidity', 'weather_condition'
                    ]].copy()
                    display_weather['timestamp'] = pd.to_datetime(
                        display_weather['timestamp']
                    ).dt.strftime('%Y-%m-%d %H:%M')

                    st.dataframe(display_weather, use_container_width=True)
                else:
                    st.info("No weather records found")

    except Exception as e:
        st.error(f"Error loading data overview: {str(e)}")

# Tab 2: Quality Checks
with tab2:
    st.header("Data Quality Checks")

    try:
        from src.data.models import DataQualityCheck

        with get_db_context() as db:
            query = select(DataQualityCheck).order_by(
                DataQualityCheck.check_timestamp.desc()
            ).limit(50)

            quality_checks = pd.read_sql(query, db.connection())

            if len(quality_checks) > 0:
                # Summary metrics
                total_checks = len(quality_checks)
                passed_checks = len(quality_checks[quality_checks['status'] == 'passed'])
                failed_checks = total_checks - passed_checks

                summary_col1, summary_col2, summary_col3 = st.columns(3)

                with summary_col1:
                    st.metric("Total Checks", total_checks)

                with summary_col2:
                    st.metric("Passed", passed_checks)
                    if passed_checks == total_checks:
                        st.success("✅ All checks passed")

                with summary_col3:
                    st.metric("Failed", failed_checks)
                    if failed_checks > 0:
                        st.error(f"❌ {failed_checks} checks failed")

                # Quality checks by table
                st.subheader("📊 Quality Checks by Table")

                checks_by_table = quality_checks.groupby(['table_name', 'status']).size().reset_index(name='count')

                fig = px.bar(
                    checks_by_table,
                    x='table_name',
                    y='count',
                    color='status',
                    title='Quality Checks by Table',
                    labels={'count': 'Number of Checks', 'table_name': 'Table'},
                    barmode='group',
                    color_discrete_map={'passed': '#4CAF50', 'failed': '#F44336'}
                )

                fig.update_layout(height=400, template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)

                # Recent checks table
                st.subheader("🔍 Recent Quality Checks")

                display_checks = quality_checks[[
                    'check_name', 'table_name', 'status', 'check_timestamp'
                ]].copy()

                display_checks['check_timestamp'] = pd.to_datetime(
                    display_checks['check_timestamp']
                ).dt.strftime('%Y-%m-%d %H:%M')

                # Add status emoji
                display_checks['status_display'] = display_checks['status'].apply(
                    lambda x: '✅ Passed' if x == 'passed' else '❌ Failed'
                )

                display_checks = display_checks[[
                    'check_name', 'table_name', 'status_display', 'check_timestamp'
                ]]

                display_checks.columns = ['Check Name', 'Table', 'Status', 'Timestamp']

                st.dataframe(display_checks, use_container_width=True)

                # Failed checks details
                if failed_checks > 0:
                    with st.expander("❌ View Failed Checks Details"):
                        failed_df = quality_checks[quality_checks['status'] == 'failed']

                        for idx, row in failed_df.iterrows():
                            st.error(f"**{row['check_name']}** ({row['table_name']})")
                            st.write(f"Error: {row['error_message']}")
                            st.write(f"Timestamp: {row['check_timestamp']}")
                            st.markdown("---")

            else:
                st.info("No quality checks recorded yet. Quality checks are logged by Airflow DAGs.")

    except Exception as e:
        st.warning(f"Could not load quality checks: {str(e)}")

# Tab 3: Data Freshness
with tab3:
    st.header("Data Freshness Monitoring")

    try:
        from src.data.models import BikeStationStatus, WeatherData, Feature

        with get_db_context() as db:
            # Check freshness of each data source
            freshness_data = []

            # Bike Station Status
            latest_status_ts = db.query(func.max(BikeStationStatus.timestamp)).scalar()
            if latest_status_ts:
                age_minutes = (datetime.utcnow() - latest_status_ts).total_seconds() / 60
                status_fresh = age_minutes < 60  # Expected every 15 min

                freshness_data.append({
                    'Data Source': 'Bike Station Status',
                    'Latest Record': latest_status_ts.strftime('%Y-%m-%d %H:%M:%S'),
                    'Age (minutes)': int(age_minutes),
                    'Expected Frequency': 'Every 15 minutes',
                    'Status': 'Fresh' if status_fresh else 'Stale'
                })

            # Weather Data
            latest_weather_ts = db.query(func.max(WeatherData.timestamp)).scalar()
            if latest_weather_ts:
                age_minutes = (datetime.utcnow() - latest_weather_ts).total_seconds() / 60
                weather_fresh = age_minutes < 90  # Expected every 30 min

                freshness_data.append({
                    'Data Source': 'Weather Data',
                    'Latest Record': latest_weather_ts.strftime('%Y-%m-%d %H:%M:%S'),
                    'Age (minutes)': int(age_minutes),
                    'Expected Frequency': 'Every 30 minutes',
                    'Status': 'Fresh' if weather_fresh else 'Stale'
                })

            # Features
            latest_feature_ts = db.query(func.max(Feature.timestamp)).scalar()
            if latest_feature_ts:
                age_minutes = (datetime.utcnow() - latest_feature_ts).total_seconds() / 60
                feature_fresh = age_minutes < 120  # Expected every hour

                freshness_data.append({
                    'Data Source': 'Engineered Features',
                    'Latest Record': latest_feature_ts.strftime('%Y-%m-%d %H:%M:%S'),
                    'Age (minutes)': int(age_minutes),
                    'Expected Frequency': 'Every hour',
                    'Status': 'Fresh' if feature_fresh else 'Stale'
                })

            if freshness_data:
                freshness_df = pd.DataFrame(freshness_data)

                # Display table
                st.dataframe(freshness_df, use_container_width=True)

                # Visual indicators
                st.subheader("📊 Freshness Status")

                for idx, row in freshness_df.iterrows():
                    col1, col2, col3 = st.columns([2, 2, 1])

                    with col1:
                        st.write(f"**{row['Data Source']}**")

                    with col2:
                        st.write(f"{row['Age (minutes)']} minutes ago")

                    with col3:
                        if row['Status'] == 'Fresh':
                            st.success("✅ Fresh")
                        else:
                            st.error("❌ Stale")

                    st.progress(min(row['Age (minutes)'] / 120, 1.0))

            else:
                st.info("No data available to check freshness")

    except Exception as e:
        st.error(f"Error checking data freshness: {str(e)}")

# Actions
st.markdown("---")
st.subheader("⚡ Actions")

action_col1, action_col2, action_col3 = st.columns(3)

with action_col1:
    if st.button("🔄 Refresh Data"):
        st.rerun()

with action_col2:
    if st.button("📊 View Airflow DAGs"):
        st.markdown("[Open Airflow UI](http://localhost:8080)")

with action_col3:
    if st.button("🗄️ View Database"):
        st.info("Connect with: psql postgresql://postgres:postgres@localhost:5432/bike_demand")
