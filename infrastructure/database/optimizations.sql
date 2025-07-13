-- JOTA News Database Optimizations for High-Volume Operations
-- This file contains database optimizations for scalability

-- =============================================
-- INDEXES FOR PERFORMANCE OPTIMIZATION
-- =============================================

-- News table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_news_created_at ON news_news (created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_news_updated_at ON news_news (updated_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_news_category_id ON news_news (category_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_news_is_urgent ON news_news (is_urgent) WHERE is_urgent = true;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_news_is_published ON news_news (is_published) WHERE is_published = true;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_news_is_processed ON news_news (is_processed);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_news_source ON news_news (source);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_news_classification_confidence ON news_news (classification_confidence DESC);

-- Composite indexes for common queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_news_published_urgent ON news_news (is_published, is_urgent, created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_news_category_published ON news_news (category_id, is_published, created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_news_source_created ON news_news (source, created_at DESC);

-- Full-text search index
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_news_title_content_search ON news_news USING gin(to_tsvector('english', title || ' ' || content));
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_news_title_search ON news_news USING gin(to_tsvector('english', title));

-- Categories table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_category_is_active ON news_category (is_active) WHERE is_active = true;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_category_name ON news_category (name);

-- Tags table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tag_name ON news_tag (name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tag_usage_count ON news_tag (usage_count DESC);

-- News-Tags many-to-many relationship
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_news_tags_news_id ON news_news_tags (news_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_news_tags_tag_id ON news_news_tags (tag_id);

-- Webhook logs indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhook_log_created_at ON webhooks_webhooklog (created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhook_log_source ON webhooks_webhooklog (source_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhook_log_status ON webhooks_webhooklog (status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhook_log_processed_at ON webhooks_webhooklog (processed_at DESC);

-- Classification results indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_classification_result_news_id ON classification_classificationresult (news_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_classification_result_category_id ON classification_classificationresult (category_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_classification_result_confidence ON classification_classificationresult (confidence_score DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_classification_result_created_at ON classification_classificationresult (created_at DESC);

-- Notification indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notification_subscription_id ON notifications_notification (subscription_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notification_news_id ON notifications_notification (news_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notification_status ON notifications_notification (status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notification_sent_at ON notifications_notification (sent_at DESC);

-- Notification subscriptions indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notification_subscription_user_id ON notifications_notificationsubscription (user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notification_subscription_channel_id ON notifications_notificationsubscription (channel_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notification_subscription_active ON notifications_notificationsubscription (is_active) WHERE is_active = true;

-- =============================================
-- PARTITIONING FOR LARGE TABLES
-- =============================================

-- Partition news table by date (monthly partitions)
-- This is for new installations. For existing data, use pg_partman extension

-- Create partitioned news table (for new installations)
CREATE TABLE IF NOT EXISTS news_news_partitioned (
    LIKE news_news INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- Create monthly partitions for current year
DO $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
BEGIN
    FOR i IN 1..12 LOOP
        start_date := DATE_TRUNC('month', DATE(EXTRACT(YEAR FROM NOW()) || '-' || i || '-01'));
        end_date := start_date + INTERVAL '1 month';
        partition_name := 'news_news_y' || EXTRACT(YEAR FROM start_date) || '_m' || LPAD(i::text, 2, '0');
        
        EXECUTE FORMAT('CREATE TABLE IF NOT EXISTS %I PARTITION OF news_news_partitioned FOR VALUES FROM (%L) TO (%L)',
                      partition_name, start_date, end_date);
    END LOOP;
END $$;

-- Create partitioned webhook logs table
CREATE TABLE IF NOT EXISTS webhooks_webhooklog_partitioned (
    LIKE webhooks_webhooklog INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- Create monthly partitions for webhook logs
DO $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
BEGIN
    FOR i IN 1..12 LOOP
        start_date := DATE_TRUNC('month', DATE(EXTRACT(YEAR FROM NOW()) || '-' || i || '-01'));
        end_date := start_date + INTERVAL '1 month';
        partition_name := 'webhooks_webhooklog_y' || EXTRACT(YEAR FROM start_date) || '_m' || LPAD(i::text, 2, '0');
        
        EXECUTE FORMAT('CREATE TABLE IF NOT EXISTS %I PARTITION OF webhooks_webhooklog_partitioned FOR VALUES FROM (%L) TO (%L)',
                      partition_name, start_date, end_date);
    END LOOP;
END $$;

-- =============================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- =============================================

-- News statistics materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_news_statistics AS
SELECT 
    DATE(created_at) as date,
    category_id,
    COUNT(*) as total_news,
    COUNT(*) FILTER (WHERE is_urgent = true) as urgent_news,
    COUNT(*) FILTER (WHERE is_published = true) as published_news,
    AVG(classification_confidence) as avg_confidence,
    AVG(view_count) as avg_views,
    AVG(share_count) as avg_shares
FROM news_news
GROUP BY DATE(created_at), category_id
ORDER BY date DESC, category_id;

-- Create unique index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_news_statistics_date_category 
ON mv_news_statistics (date, category_id);

-- Category statistics materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_category_statistics AS
SELECT 
    c.id as category_id,
    c.name as category_name,
    COUNT(n.id) as total_news,
    COUNT(n.id) FILTER (WHERE n.is_urgent = true) as urgent_news,
    COUNT(n.id) FILTER (WHERE n.created_at >= NOW() - INTERVAL '7 days') as recent_news,
    AVG(n.classification_confidence) as avg_confidence,
    MAX(n.created_at) as last_news_date
FROM news_category c
LEFT JOIN news_news n ON c.id = n.category_id
WHERE c.is_active = true
GROUP BY c.id, c.name
ORDER BY total_news DESC;

-- Create unique index on category statistics
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_category_statistics_category_id 
ON mv_category_statistics (category_id);

-- Top tags materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_top_tags AS
SELECT 
    t.id as tag_id,
    t.name as tag_name,
    COUNT(nt.news_id) as usage_count,
    COUNT(nt.news_id) FILTER (WHERE n.created_at >= NOW() - INTERVAL '7 days') as recent_usage,
    MAX(n.created_at) as last_used_date
FROM news_tag t
LEFT JOIN news_news_tags nt ON t.id = nt.tag_id
LEFT JOIN news_news n ON nt.news_id = n.id
GROUP BY t.id, t.name
ORDER BY usage_count DESC
LIMIT 1000;

-- Create unique index on top tags
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_top_tags_tag_id 
ON mv_top_tags (tag_id);

-- =============================================
-- STORED PROCEDURES FOR COMMON OPERATIONS
-- =============================================

-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_news_statistics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_category_statistics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_top_tags;
END;
$$ LANGUAGE plpgsql;

-- Function to get news with full-text search
CREATE OR REPLACE FUNCTION search_news(
    search_query TEXT,
    limit_count INTEGER DEFAULT 20,
    offset_count INTEGER DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    content TEXT,
    source TEXT,
    created_at TIMESTAMP,
    category_name TEXT,
    relevance REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        n.id,
        n.title,
        n.content,
        n.source,
        n.created_at,
        c.name as category_name,
        ts_rank(to_tsvector('english', n.title || ' ' || n.content), 
                plainto_tsquery('english', search_query)) as relevance
    FROM news_news n
    LEFT JOIN news_category c ON n.category_id = c.id
    WHERE to_tsvector('english', n.title || ' ' || n.content) @@ plainto_tsquery('english', search_query)
    AND n.is_published = true
    ORDER BY relevance DESC, n.created_at DESC
    LIMIT limit_count OFFSET offset_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get trending news
CREATE OR REPLACE FUNCTION get_trending_news(
    hours_back INTEGER DEFAULT 24,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    view_count INTEGER,
    share_count INTEGER,
    created_at TIMESTAMP,
    category_name TEXT,
    trending_score REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        n.id,
        n.title,
        n.view_count,
        n.share_count,
        n.created_at,
        c.name as category_name,
        (n.view_count * 1.0 + n.share_count * 2.0) / 
        EXTRACT(EPOCH FROM (NOW() - n.created_at))/3600 as trending_score
    FROM news_news n
    LEFT JOIN news_category c ON n.category_id = c.id
    WHERE n.created_at >= NOW() - INTERVAL '1 hour' * hours_back
    AND n.is_published = true
    ORDER BY trending_score DESC, n.created_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Function to clean old data
CREATE OR REPLACE FUNCTION cleanup_old_data(
    days_to_keep INTEGER DEFAULT 90
)
RETURNS void AS $$
BEGIN
    -- Delete old webhook logs
    DELETE FROM webhooks_webhooklog 
    WHERE created_at < NOW() - INTERVAL '1 day' * days_to_keep;
    
    -- Delete old classification results (keep more for training)
    DELETE FROM classification_classificationresult 
    WHERE created_at < NOW() - INTERVAL '1 day' * (days_to_keep * 2);
    
    -- Delete old notifications
    DELETE FROM notifications_notification 
    WHERE sent_at < NOW() - INTERVAL '1 day' * days_to_keep;
    
    -- Vacuum tables
    VACUUM ANALYZE;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- DATABASE CONFIGURATION FOR PERFORMANCE
-- =============================================

-- Optimize PostgreSQL settings for high-volume operations
-- These should be set in postgresql.conf or via ALTER SYSTEM

-- Memory settings
-- shared_buffers = 25% of RAM
-- effective_cache_size = 75% of RAM
-- work_mem = 4MB to 32MB depending on concurrent connections
-- maintenance_work_mem = 256MB to 1GB

-- Connection settings
-- max_connections = 100 to 200 (use connection pooling)
-- max_prepared_transactions = 100

-- Checkpoint settings
-- checkpoint_completion_target = 0.9
-- wal_buffers = 16MB
-- checkpoint_timeout = 10min

-- Query planner settings
-- random_page_cost = 1.1 (for SSD)
-- effective_io_concurrency = 200 (for SSD)

-- Logging settings for monitoring
-- log_min_duration_statement = 1000 (log queries > 1 second)
-- log_statement = 'mod' (log all modifications)

-- =============================================
-- MONITORING QUERIES
-- =============================================

-- Query to monitor slow queries
CREATE OR REPLACE VIEW slow_queries AS
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    min_time,
    max_time,
    stddev_time
FROM pg_stat_statements
WHERE mean_time > 100  -- queries taking more than 100ms on average
ORDER BY mean_time DESC;

-- Query to monitor table sizes
CREATE OR REPLACE VIEW table_sizes AS
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
FROM pg_tables
WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
ORDER BY size_bytes DESC;

-- Query to monitor index usage
CREATE OR REPLACE VIEW index_usage AS
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexname)) as index_size
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- =============================================
-- AUTOMATED MAINTENANCE JOBS
-- =============================================

-- Create function to be called by cron job
CREATE OR REPLACE FUNCTION daily_maintenance()
RETURNS void AS $$
BEGIN
    -- Refresh materialized views
    PERFORM refresh_all_materialized_views();
    
    -- Update table statistics
    ANALYZE;
    
    -- Cleanup old data (keep 90 days)
    PERFORM cleanup_old_data(90);
    
    -- Log maintenance completion
    INSERT INTO system_maintenance_log (operation, completed_at)
    VALUES ('daily_maintenance', NOW());
END;
$$ LANGUAGE plpgsql;

-- Create maintenance log table
CREATE TABLE IF NOT EXISTS system_maintenance_log (
    id SERIAL PRIMARY KEY,
    operation VARCHAR(100) NOT NULL,
    completed_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =============================================
-- COMMENTS FOR DOCUMENTATION
-- =============================================

COMMENT ON INDEX idx_news_created_at IS 'Index for sorting news by creation date';
COMMENT ON INDEX idx_news_title_content_search IS 'Full-text search index for news titles and content';
COMMENT ON MATERIALIZED VIEW mv_news_statistics IS 'Daily news statistics aggregated by date and category';
COMMENT ON FUNCTION search_news IS 'Full-text search function with relevance ranking';
COMMENT ON FUNCTION get_trending_news IS 'Function to get trending news based on views and shares';
COMMENT ON FUNCTION daily_maintenance IS 'Daily maintenance routine to refresh views and cleanup data';