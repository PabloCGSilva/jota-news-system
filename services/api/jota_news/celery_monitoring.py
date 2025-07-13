"""
Celery monitoring and metrics collection for Prometheus.
"""
import time
import logging
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge, Info
from celery import current_app
from celery.signals import (
    task_prerun, task_postrun, task_failure, task_success,
    worker_ready, worker_shutdown, task_retry
)

logger = logging.getLogger(__name__)

# Prometheus metrics
CELERY_TASK_COUNTER = Counter(
    'celery_tasks_total',
    'Total number of Celery tasks',
    ['task_name', 'status']
)

CELERY_TASK_DURATION = Histogram(
    'celery_task_duration_seconds',
    'Time spent processing Celery tasks',
    ['task_name'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float('inf')]
)

CELERY_QUEUE_LENGTH = Gauge(
    'celery_queue_length',
    'Number of tasks in Celery queues',
    ['queue_name']
)

CELERY_ACTIVE_WORKERS = Gauge(
    'celery_active_workers',
    'Number of active Celery workers'
)

CELERY_WORKER_INFO = Info(
    'celery_worker_info',
    'Information about Celery workers'
)

CELERY_TASK_RETRY_COUNTER = Counter(
    'celery_task_retries_total',
    'Total number of task retries',
    ['task_name', 'exception']
)

# Store task start times
task_start_times = {}


class CeleryMonitor:
    """Celery monitoring class for collecting metrics."""
    
    def __init__(self):
        self.active_tasks = set()
        self.worker_count = 0
    
    def get_queue_lengths(self):
        """Get current queue lengths."""
        try:
            inspect = current_app.control.inspect()
            active_queues = inspect.active_queues()
            
            if active_queues:
                for worker, queues in active_queues.items():
                    for queue in queues:
                        queue_name = queue['name']
                        # This is a simplified approach - in production you'd want
                        # to connect to the broker directly for accurate counts
                        CELERY_QUEUE_LENGTH.labels(queue_name=queue_name).set(0)
        except Exception as e:
            logger.error(f"Error getting queue lengths: {e}")
    
    def update_worker_count(self):
        """Update active worker count."""
        try:
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            if stats:
                self.worker_count = len(stats)
                CELERY_ACTIVE_WORKERS.set(self.worker_count)
        except Exception as e:
            logger.error(f"Error updating worker count: {e}")


# Global monitor instance
celery_monitor = CeleryMonitor()


def monitor_task(func):
    """Decorator to monitor Celery tasks."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        task_name = func.__name__
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            CELERY_TASK_COUNTER.labels(
                task_name=task_name,
                status='success'
            ).inc()
            return result
        except Exception as e:
            CELERY_TASK_COUNTER.labels(
                task_name=task_name,
                status='failure'
            ).inc()
            raise
        finally:
            duration = time.time() - start_time
            CELERY_TASK_DURATION.labels(task_name=task_name).observe(duration)
    
    return wrapper


# Signal handlers
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task pre-run signal."""
    task_name = sender.__name__ if sender else 'unknown'
    task_start_times[task_id] = time.time()
    celery_monitor.active_tasks.add(task_id)
    logger.info(f"Task {task_name} (ID: {task_id}) started")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Handle task post-run signal."""
    task_name = sender.__name__ if sender else 'unknown'
    
    # Calculate duration
    if task_id in task_start_times:
        duration = time.time() - task_start_times[task_id]
        CELERY_TASK_DURATION.labels(task_name=task_name).observe(duration)
        del task_start_times[task_id]
    
    # Remove from active tasks
    celery_monitor.active_tasks.discard(task_id)
    
    logger.info(f"Task {task_name} (ID: {task_id}) completed with state: {state}")


@task_success.connect
def task_success_handler(sender=None, result=None, **kwds):
    """Handle task success signal."""
    task_name = sender.__name__ if sender else 'unknown'
    CELERY_TASK_COUNTER.labels(
        task_name=task_name,
        status='success'
    ).inc()


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Handle task failure signal."""
    task_name = sender.__name__ if sender else 'unknown'
    exception_name = exception.__class__.__name__ if exception else 'unknown'
    
    CELERY_TASK_COUNTER.labels(
        task_name=task_name,
        status='failure'
    ).inc()
    
    logger.error(f"Task {task_name} (ID: {task_id}) failed with exception: {exception_name}")


@task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwds):
    """Handle task retry signal."""
    task_name = sender.__name__ if sender else 'unknown'
    exception_name = reason.__class__.__name__ if reason else 'unknown'
    
    CELERY_TASK_RETRY_COUNTER.labels(
        task_name=task_name,
        exception=exception_name
    ).inc()
    
    logger.warning(f"Task {task_name} (ID: {task_id}) retrying due to: {exception_name}")


@worker_ready.connect
def worker_ready_handler(sender=None, **kwds):
    """Handle worker ready signal."""
    celery_monitor.worker_count += 1
    CELERY_ACTIVE_WORKERS.set(celery_monitor.worker_count)
    logger.info(f"Worker ready: {sender}")


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwds):
    """Handle worker shutdown signal."""
    celery_monitor.worker_count = max(0, celery_monitor.worker_count - 1)
    CELERY_ACTIVE_WORKERS.set(celery_monitor.worker_count)
    logger.info(f"Worker shutdown: {sender}")


def get_celery_metrics():
    """Get current Celery metrics as a dictionary."""
    celery_monitor.get_queue_lengths()
    celery_monitor.update_worker_count()
    
    return {
        'active_workers': celery_monitor.worker_count,
        'active_tasks': len(celery_monitor.active_tasks),
        'total_tasks': sum([
            family.samples[0].value 
            for family in CELERY_TASK_COUNTER.collect()
            for sample in family.samples
        ]),
    }