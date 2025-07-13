"""
Database connection pooling and optimization for JOTA News System
Implements connection pooling, read/write splitting, and query optimization
"""

import os
import logging
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import redis
from functools import wraps
import time
import hashlib
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DatabaseConnectionPool:
    """
    Advanced database connection pool with read/write splitting and caching
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.write_pool = None
        self.read_pool = None
        self.redis_client = None
        self._initialize_pools()
        self._initialize_cache()
    
    def _initialize_pools(self):
        """Initialize connection pools for read and write operations"""
        try:
            # Write pool (master database)
            self.write_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self.config.get('write_pool_min', 5),
                maxconn=self.config.get('write_pool_max', 20),
                host=self.config.get('write_host', 'localhost'),
                port=self.config.get('write_port', 5432),
                database=self.config.get('database', 'jota_news'),
                user=self.config.get('username'),
                password=self.config.get('password'),
                cursor_factory=RealDictCursor,
                application_name='jota-news-write'
            )
            
            # Read pool (replica database or same as write if no replica)
            read_host = self.config.get('read_host', self.config.get('write_host', 'localhost'))
            self.read_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self.config.get('read_pool_min', 10),
                maxconn=self.config.get('read_pool_max', 50),
                host=read_host,
                port=self.config.get('read_port', self.config.get('write_port', 5432)),
                database=self.config.get('database', 'jota_news'),
                user=self.config.get('username'),
                password=self.config.get('password'),
                cursor_factory=RealDictCursor,
                application_name='jota-news-read'
            )
            
            logger.info("Database connection pools initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database pools: {str(e)}")
            raise
    
    def _initialize_cache(self):
        """Initialize Redis cache for query caching"""
        try:
            redis_url = self.config.get('redis_url', 'redis://localhost:6379/1')
            self.redis_client = redis.from_url(redis_url)
            self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
            
        except Exception as e:
            logger.warning(f"Redis cache initialization failed: {str(e)}")
            self.redis_client = None
    
    @contextmanager
    def get_connection(self, read_only: bool = False):
        """
        Context manager for database connections
        
        Args:
            read_only: Whether this is a read-only operation
        
        Yields:
            Database connection
        """
        pool = self.read_pool if read_only else self.write_pool
        connection = None
        
        try:
            connection = pool.getconn()
            if not read_only:
                connection.autocommit = False
            yield connection
            
        except Exception as e:
            if connection and not read_only:
                connection.rollback()
            logger.error(f"Database connection error: {str(e)}")
            raise
        finally:
            if connection:
                if not read_only:
                    connection.commit()
                pool.putconn(connection)
    
    def execute_query(self, query: str, params: Optional[tuple] = None, 
                     read_only: bool = False, cache_ttl: int = 300) -> List[Dict[str, Any]]:
        """
        Execute a database query with optional caching
        
        Args:
            query: SQL query string
            params: Query parameters
            read_only: Whether this is a read-only query
            cache_ttl: Cache time-to-live in seconds
        
        Returns:
            List of query results
        """
        # Generate cache key for read-only queries
        cache_key = None
        if read_only and self.redis_client and cache_ttl > 0:
            cache_key = self._generate_cache_key(query, params)
            
            # Try to get from cache
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return cached_result
        
        # Execute query
        with self.get_connection(read_only=read_only) as conn:
            with conn.cursor() as cursor:
                start_time = time.time()
                cursor.execute(query, params)
                
                if query.strip().upper().startswith('SELECT'):
                    results = cursor.fetchall()
                    # Convert to list of dicts
                    results = [dict(row) for row in results]
                else:
                    results = []
                
                execution_time = time.time() - start_time
                logger.debug(f"Query executed in {execution_time:.3f}s: {query[:50]}...")
                
                # Cache the result if it's a read-only query
                if cache_key and results:
                    self._set_cache(cache_key, results, cache_ttl)
                
                return results
    
    def execute_transaction(self, queries: List[Dict[str, Any]]) -> bool:
        """
        Execute multiple queries in a transaction
        
        Args:
            queries: List of query dictionaries with 'query' and 'params' keys
        
        Returns:
            Success status
        """
        try:
            with self.get_connection(read_only=False) as conn:
                with conn.cursor() as cursor:
                    for query_info in queries:
                        cursor.execute(query_info['query'], query_info.get('params'))
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            return False
    
    def _generate_cache_key(self, query: str, params: Optional[tuple] = None) -> str:
        """Generate cache key for query and parameters"""
        key_data = f"{query}:{params}" if params else query
        return f"jota_news:query:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached query result"""
        try:
            if not self.redis_client:
                return None
                
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data.decode())
            return None
            
        except Exception as e:
            logger.warning(f"Cache read error: {str(e)}")
            return None
    
    def _set_cache(self, cache_key: str, data: List[Dict[str, Any]], ttl: int):
        """Set query result in cache"""
        try:
            if not self.redis_client:
                return
                
            # Convert datetime objects to strings for JSON serialization
            serializable_data = self._make_serializable(data)
            self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(serializable_data, default=str)
            )
            
        except Exception as e:
            logger.warning(f"Cache write error: {str(e)}")
    
    def _make_serializable(self, data: Any) -> Any:
        """Convert data to JSON-serializable format"""
        if isinstance(data, list):
            return [self._make_serializable(item) for item in data]
        elif isinstance(data, dict):
            return {key: self._make_serializable(value) for key, value in data.items()}
        elif isinstance(data, datetime):
            return data.isoformat()
        else:
            return data
    
    def invalidate_cache(self, pattern: str = "jota_news:query:*"):
        """Invalidate cached queries"""
        try:
            if not self.redis_client:
                return
                
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cached queries")
                
        except Exception as e:
            logger.warning(f"Cache invalidation error: {str(e)}")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        return {
            'write_pool': {
                'total_connections': self.write_pool.maxconn,
                'available_connections': len(self.write_pool._pool),
                'used_connections': self.write_pool.maxconn - len(self.write_pool._pool)
            },
            'read_pool': {
                'total_connections': self.read_pool.maxconn,
                'available_connections': len(self.read_pool._pool),
                'used_connections': self.read_pool.maxconn - len(self.read_pool._pool)
            }
        }
    
    def close_all_connections(self):
        """Close all connection pools"""
        if self.write_pool:
            self.write_pool.closeall()
        if self.read_pool:
            self.read_pool.closeall()
        if self.redis_client:
            self.redis_client.close()
        logger.info("All database connections closed")

# Decorator for query caching
def cached_query(ttl: int = 300):
    """
    Decorator for caching database queries
    
    Args:
        ttl: Cache time-to-live in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key based on function name and arguments
            cache_key = f"jota_news:func:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            if hasattr(wrapper, 'redis_client') and wrapper.redis_client:
                try:
                    cached_result = wrapper.redis_client.get(cache_key)
                    if cached_result:
                        return json.loads(cached_result.decode())
                except Exception:
                    pass
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache the result
            if hasattr(wrapper, 'redis_client') and wrapper.redis_client:
                try:
                    wrapper.redis_client.setex(
                        cache_key,
                        ttl,
                        json.dumps(result, default=str)
                    )
                except Exception:
                    pass
            
            return result
        
        return wrapper
    return decorator

# High-level database operations
class NewsDatabase:
    """
    High-level database operations for JOTA News System
    """
    
    def __init__(self, connection_pool: DatabaseConnectionPool):
        self.pool = connection_pool
    
    @cached_query(ttl=600)  # Cache for 10 minutes
    def get_news_by_category(self, category_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get news articles by category"""
        query = """
            SELECT n.id, n.title, n.content, n.source, n.created_at, n.view_count, n.share_count,
                   c.name as category_name, n.is_urgent, n.is_published
            FROM news_news n
            LEFT JOIN news_category c ON n.category_id = c.id
            WHERE n.category_id = %s AND n.is_published = true
            ORDER BY n.created_at DESC
            LIMIT %s OFFSET %s
        """
        return self.pool.execute_query(query, (category_id, limit, offset), read_only=True)
    
    @cached_query(ttl=300)  # Cache for 5 minutes
    def get_trending_news(self, hours: int = 24, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending news using stored function"""
        query = "SELECT * FROM get_trending_news(%s, %s)"
        return self.pool.execute_query(query, (hours, limit), read_only=True)
    
    @cached_query(ttl=1800)  # Cache for 30 minutes
    def get_news_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get news statistics from materialized view"""
        query = """
            SELECT date, category_id, total_news, urgent_news, published_news, 
                   avg_confidence, avg_views, avg_shares
            FROM mv_news_statistics
            WHERE date >= %s
            ORDER BY date DESC
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        results = self.pool.execute_query(query, (cutoff_date.date(),), read_only=True, cache_ttl=1800)
        
        # Aggregate statistics
        stats = {
            'total_news': sum(r['total_news'] for r in results),
            'urgent_news': sum(r['urgent_news'] for r in results),
            'published_news': sum(r['published_news'] for r in results),
            'avg_confidence': sum(r['avg_confidence'] or 0 for r in results) / len(results) if results else 0,
            'daily_breakdown': results
        }
        
        return stats
    
    def create_news_article(self, news_data: Dict[str, Any]) -> str:
        """Create a new news article"""
        query = """
            INSERT INTO news_news (id, title, content, source, author, category_id, 
                                 is_urgent, is_published, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        import uuid
        news_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        params = (
            news_id,
            news_data['title'],
            news_data['content'],
            news_data['source'],
            news_data.get('author'),
            news_data.get('category_id'),
            news_data.get('is_urgent', False),
            news_data.get('is_published', True),
            now,
            now
        )
        
        result = self.pool.execute_query(query, params, read_only=False)
        
        # Invalidate related caches
        self.pool.invalidate_cache("jota_news:query:*")
        
        return news_id
    
    def update_news_views(self, news_id: str) -> bool:
        """Update news view count"""
        query = """
            UPDATE news_news 
            SET view_count = view_count + 1, updated_at = %s
            WHERE id = %s
        """
        
        result = self.pool.execute_query(query, (datetime.utcnow(), news_id), read_only=False)
        return True
    
    def search_news(self, search_query: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Search news using full-text search function"""
        query = "SELECT * FROM search_news(%s, %s, %s)"
        return self.pool.execute_query(query, (search_query, limit, offset), read_only=True, cache_ttl=60)
    
    def get_category_statistics(self) -> List[Dict[str, Any]]:
        """Get category statistics from materialized view"""
        query = "SELECT * FROM mv_category_statistics ORDER BY total_news DESC"
        return self.pool.execute_query(query, read_only=True, cache_ttl=900)  # Cache for 15 minutes
    
    def refresh_materialized_views(self) -> bool:
        """Refresh all materialized views"""
        query = "SELECT refresh_all_materialized_views()"
        try:
            self.pool.execute_query(query, read_only=False)
            # Invalidate all cached queries since views are refreshed
            self.pool.invalidate_cache()
            return True
        except Exception as e:
            logger.error(f"Error refreshing materialized views: {str(e)}")
            return False

# Django integration
class DjangoConnectionPoolMiddleware:
    """Django middleware for database connection pooling"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.pool = None
    
    def __call__(self, request):
        if not self.pool:
            self.pool = self._initialize_pool()
        
        # Attach pool to request
        request.db_pool = self.pool
        
        response = self.get_response(request)
        return response
    
    def _initialize_pool(self):
        """Initialize connection pool from Django settings"""
        from django.conf import settings
        
        db_config = settings.DATABASES['default']
        pool_config = {
            'write_host': db_config['HOST'],
            'write_port': db_config['PORT'],
            'database': db_config['NAME'],
            'username': db_config['USER'],
            'password': db_config['PASSWORD'],
            'redis_url': getattr(settings, 'REDIS_URL', 'redis://localhost:6379/1'),
            'write_pool_min': getattr(settings, 'DB_WRITE_POOL_MIN', 5),
            'write_pool_max': getattr(settings, 'DB_WRITE_POOL_MAX', 20),
            'read_pool_min': getattr(settings, 'DB_READ_POOL_MIN', 10),
            'read_pool_max': getattr(settings, 'DB_READ_POOL_MAX', 50),
        }
        
        return DatabaseConnectionPool(pool_config)

# Example usage
def example_usage():
    """Example of how to use the database connection pool"""
    
    # Initialize connection pool
    config = {
        'write_host': 'localhost',
        'write_port': 5432,
        'database': 'jota_news',
        'username': 'postgres',
        'password': 'password',
        'redis_url': 'redis://localhost:6379/1'
    }
    
    pool = DatabaseConnectionPool(config)
    news_db = NewsDatabase(pool)
    
    # Get trending news
    trending = news_db.get_trending_news(hours=24, limit=10)
    print(f"Found {len(trending)} trending articles")
    
    # Search news
    search_results = news_db.search_news("technology", limit=5)
    print(f"Found {len(search_results)} articles about technology")
    
    # Get statistics
    stats = news_db.get_news_statistics(days=7)
    print(f"Total news in last 7 days: {stats['total_news']}")
    
    # Close connections
    pool.close_all_connections()

if __name__ == "__main__":
    example_usage()