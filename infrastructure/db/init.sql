-- Initialize JOTA News Database
-- This file is run when the PostgreSQL container starts

-- Create database if it doesn't exist
-- SELECT 'CREATE DATABASE jota_news' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'jota_news');

-- Create extensions for better performance and full-text search
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Create indexes for better performance (will be created by Django migrations)
-- These are just examples of what Django will create

-- Example of full-text search configuration for Portuguese
-- This helps with news content search
CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS portuguese_unaccent (COPY = portuguese);
ALTER TEXT SEARCH CONFIGURATION portuguese_unaccent
    ALTER MAPPING FOR hword, hword_part, word WITH unaccent, portuguese_stem;