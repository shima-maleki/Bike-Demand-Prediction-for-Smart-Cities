-- PostgreSQL Initialization Script
-- This script runs when the PostgreSQL container is first created

-- Note: Database is already created by Docker environment variable POSTGRES_DB
-- Connecting to the default database (bike_demand)

-- Create user (password will be set via environment variables)
-- CREATE USER bike_demand_user WITH PASSWORD 'change_this_password';

-- Grant privileges
-- GRANT ALL PRIVILEGES ON DATABASE bike_demand TO bike_demand_user;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search
CREATE EXTENSION IF NOT EXISTS "btree_gin";  -- For JSONB indexing

-- Create schema (optional, using public for now)
-- CREATE SCHEMA IF NOT EXISTS bike_demand;
-- GRANT ALL ON SCHEMA bike_demand TO bike_demand_user;

-- Log initialization
SELECT 'Database initialized successfully' AS status;
