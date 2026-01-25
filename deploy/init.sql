-- ASTRAEUS Database Initialization Script
-- This script runs automatically when PostgreSQL container starts

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create indexes for performance
-- (Tables are created by SQLAlchemy, this is for additional optimization)

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'ASTRAEUS database initialized at %', NOW();
END $$;
