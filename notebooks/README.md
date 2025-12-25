# 📓 Notebooks

Jupyter notebooks for data exploration, experimentation, and system demonstration.

## Available Notebooks

### 00_end_to_end_system_demo.ipynb
**Complete system demonstration notebook**

This comprehensive notebook walks through the entire bike demand prediction system:

1. **Data Collection Pipeline**
   - Collect real-time data from NYC Citi Bike API (~1,700 stations)
   - Fetch weather data from OpenWeatherMap API
   - Save raw data to `data/raw/` folder

2. **Feature Engineering** (100+ features)
   - Temporal features: hour, day, season, is_weekend, rush_hour, cyclic encoding
   - Lag features: 1h, 3h, 6h, 12h, 24h, 48h, 168h
   - Rolling features: 3h, 6h, 12h, 24h (mean, std, min, max)
   - Weather features: temperature normalized, humidity categories, wind, precipitation
   - Holiday features: US holidays, days to next holiday
   - Save processed features to `data/processed/` folder

3. **Model Training with MLflow**
   - Train XGBoost, LightGBM, and CatBoost models
   - Track all experiments in MLflow (http://localhost:5000)
   - Evaluate with RMSE, MAE, MAPE, R² metrics
   - Save models to `models/` folder
   - Generate prediction visualizations

4. **Predictions & Forecasting**
   - Single prediction examples
   - Batch predictions (24 hours)
   - Multi-day forecasts (7 days)
   - Confidence intervals

5. **Monitoring & Analysis**
   - Feature importance analysis
   - Error analysis by time of day
   - Model performance visualization
   - Data drift detection readiness

## Prerequisites

Before running the notebooks:

1. **Install dependencies**:
   ```bash
   uv sync
   # or
   pip install -e .
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenWeatherMap API key
   ```

3. **Start MLflow (optional)**:
   ```bash
   docker-compose up -d mlflow
   # Or run locally:
   mlflow server --host 0.0.0.0 --port 5000
   ```

4. **Start Jupyter**:
   ```bash
   jupyter notebook
   # or
   jupyter lab
   ```

## Outputs

The notebooks will create the following structure:

```
data/
├── raw/                    # Raw API data
│   ├── stations_*.csv
│   ├── statuses_*.csv
│   └── weather_*.csv
├── processed/              # Processed features
│   └── features_*.csv
└── *.png                   # Visualizations

models/
├── xgboost_*.json         # XGBoost model
├── lightgbm_*.txt         # LightGBM model
└── catboost_*.cbm         # CatBoost model
```

## Quick Start

Open `00_end_to_end_system_demo.ipynb` and run all cells:

```bash
jupyter notebook notebooks/00_end_to_end_system_demo.ipynb
```

The notebook is fully self-contained and will:
- ✅ Collect live data from APIs
- ✅ Engineer 100+ features
- ✅ Train 3 models with MLflow tracking
- ✅ Generate predictions and visualizations
- ✅ Save everything to appropriate folders

Expected runtime: ~10-15 minutes

## Next Steps

After running the demo notebook:

1. **View MLflow experiments**: http://localhost:5000
2. **Test FastAPI**: http://localhost:8000/docs
3. **Open Streamlit dashboard**: http://localhost:8501
4. **Set up Airflow DAGs** for production automation
5. **Configure monitoring** with Prometheus + Grafana

## Tips

- **Data persistence**: All data is saved to `data/` and `models/` folders
- **MLflow tracking**: View all experiments at http://localhost:5000
- **Reproducibility**: Models use `random_state=42` for consistency
- **Visualizations**: All plots are saved to the `data/` folder

## Troubleshooting

**MLflow connection error**:
```bash
docker-compose up -d mlflow
# or
mlflow server --host 0.0.0.0 --port 5000
```

**API key error**:
- Make sure you have a valid OpenWeatherMap API key in `.env`
- For demo purposes without weather data, you can skip weather-related cells

**Import errors**:
```bash
# Make sure you're in the project root
cd /path/to/Bike-Demand-Prediction-for-Smart-Cities
uv sync
```

## Additional Notebooks

You can create more notebooks for specific tasks:
- `01_eda.ipynb` - Exploratory data analysis
- `02_feature_selection.ipynb` - Feature engineering experiments
- `03_model_comparison.ipynb` - Advanced model comparisons
- `04_hyperparameter_tuning.ipynb` - Optuna optimization

---

**Happy Experimenting! 🚀**
