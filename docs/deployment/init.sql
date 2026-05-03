-- PostgreSQL initialization script for StackSense
-- This script runs automatically when the PostgreSQL container starts

-- Create extensions if needed
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- The tables will be created automatically by SQLAlchemy
-- This file can be used for custom initialization if needed

-- Example: Create a read-only user for analytics
-- CREATE USER stacksense_readonly WITH PASSWORD 'readonly_password';
-- GRANT CONNECT ON DATABASE stacksense TO stacksense_readonly;
-- GRANT USAGE ON SCHEMA public TO stacksense_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO stacksense_readonly;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO stacksense_readonly;

