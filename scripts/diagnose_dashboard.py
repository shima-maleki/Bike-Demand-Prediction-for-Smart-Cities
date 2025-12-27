#!/usr/bin/env python3
"""
Comprehensive Dashboard Diagnostic Script
Runs inside the dashboard container to identify connection issues
"""
import os
import sys
import requests
import json
from datetime import datetime

print("=" * 80)
print("STREAMLIT DASHBOARD DIAGNOSTIC REPORT")
print("=" * 80)
print(f"Timestamp: {datetime.utcnow().isoformat()}")
print()

# 1. Check Environment Variables
print("[1] ENVIRONMENT VARIABLES")
print("-" * 80)
api_url = os.getenv('API_URL')
db_host = os.getenv('DB_HOST')
mlflow_uri = os.getenv('MLFLOW_TRACKING_URI')

print(f"API_URL:              {api_url}")
print(f"DB_HOST:              {db_host}")
print(f"MLFLOW_TRACKING_URI:  {mlflow_uri}")
print()

# 2. Test API Health Endpoint
print("[2] API HEALTH CHECK")
print("-" * 80)
try:
    response = requests.get(f"{api_url}/health", timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    health_ok = response.status_code == 200
    print(f"✅ API /health is WORKING" if health_ok else f"❌ API /health FAILED")
except Exception as e:
    print(f"❌ ERROR: {e}")
    health_ok = False
print()

# 3. Test API Detailed Health
print("[3] API DETAILED HEALTH CHECK")
print("-" * 80)
try:
    response = requests.get(f"{api_url}/health/detailed", timeout=5)
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Overall Status: {data.get('status')}")

    components = data.get('components', {})
    for comp_name, comp_data in components.items():
        status = comp_data.get('status', 'unknown')
        symbol = "✅" if status == 'healthy' else "⚠️" if status == 'degraded' else "❌"
        print(f"  {symbol} {comp_name}: {status}")

    detailed_ok = response.status_code == 200
    print(f"\n✅ API /health/detailed is WORKING" if detailed_ok else f"❌ API /health/detailed FAILED")
except Exception as e:
    print(f"❌ ERROR: {e}")
    detailed_ok = False
print()

# 4. Test Model Info Endpoint
print("[4] MODEL INFO CHECK")
print("-" * 80)
try:
    response = requests.get(f"{api_url}/monitoring/models/current", timeout=5)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        model_info = data.get('model_info', {})
        print(f"Model Name: {model_info.get('name')}")
        print(f"Model Version: {model_info.get('version')}")
        print(f"Model Stage: {model_info.get('stage')}")
        metrics = data.get('metrics', {})
        if metrics:
            print(f"Test RMSE: {metrics.get('test_rmse')}")
            print(f"Test R²: {metrics.get('test_r2')}")
        print("✅ Model endpoint is WORKING")
    else:
        print(f"❌ Unexpected status code: {response.status_code}")
except Exception as e:
    print(f"❌ ERROR: {e}")
print()

# 5. Test Database Connection
print("[5] DATABASE CONNECTION CHECK")
print("-" * 80)
try:
    from src.config.database import get_db_context
    from sqlalchemy import text

    with get_db_context() as db:
        result = db.execute(text("SELECT 1")).scalar()
        if result == 1:
            print("✅ Database connection SUCCESSFUL")

            # Check data counts
            tables = ['bike_stations', 'features', 'bike_station_status']
            for table in tables:
                count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"  - {table}: {count:,} records")
        else:
            print("❌ Database query returned unexpected result")
except Exception as e:
    print(f"❌ ERROR: {e}")
print()

# 6. Test MLflow Connection
print("[6] MLFLOW CONNECTION CHECK")
print("-" * 80)
try:
    import mlflow
    mlflow.set_tracking_uri(mlflow_uri)
    client = mlflow.tracking.MlflowClient()

    # Try to list experiments
    experiments = client.search_experiments(max_results=1)
    print(f"✅ MLflow connection SUCCESSFUL")
    print(f"  - Found {len(experiments)} experiment(s)")

    # Try to get production model
    try:
        model_name = "bike-demand-forecasting"
        versions = client.get_latest_versions(model_name, stages=["Production"])
        if versions:
            v = versions[0]
            print(f"  - Production Model: {model_name} v{v.version}")
        else:
            print(f"  ⚠️ No Production model found")
    except:
        print(f"  ⚠️ Could not get model versions")

except Exception as e:
    print(f"❌ ERROR: {e}")
print()

# 7. Summary
print("=" * 80)
print("DIAGNOSTIC SUMMARY")
print("=" * 80)

all_checks = [
    ("Environment Variables", api_url is not None),
    ("API Health", health_ok),
    ("API Detailed Health", detailed_ok),
]

passed = sum(1 for _, ok in all_checks if ok)
total = len(all_checks)

for check_name, ok in all_checks:
    symbol = "✅" if ok else "❌"
    print(f"{symbol} {check_name}")

print()
print(f"RESULT: {passed}/{total} checks passed")

if passed == total:
    print("\n🎉 ALL CHECKS PASSED - Dashboard should be working!")
    print("\nIf you still see errors in browser:")
    print("1. Clear browser cache completely (Cmd+Shift+Delete)")
    print("2. Close ALL tabs with localhost:8501")
    print("3. Open in NEW incognito window")
    print("4. Hard refresh with Cmd+Shift+R")
else:
    print("\n⚠️ SOME CHECKS FAILED - See details above")

print("=" * 80)
