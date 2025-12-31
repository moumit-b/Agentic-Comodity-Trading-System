-- Initialize trading_system database
-- This script runs automatically when PostgreSQL container starts for the first time

-- Create extension for partitioning support (if needed)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE trading_system TO postgres;

-- Log initialization
SELECT 'Trading system database initialized successfully' AS status;
