import time
from functools import wraps
import asyncio
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Define metrics
SEARCH_REQUESTS = Counter(
    "khive_reader_search_requests_total",
    "Total number of search requests",
    ["status"]
)

SEARCH_LATENCY = Histogram(
    "khive_reader_search_latency_seconds",
    "Search request latency in seconds",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
)

INGESTION_REQUESTS = Counter(
    "khive_reader_ingestion_requests_total",
    "Total number of document ingestion requests",
    ["status"]
)

INGESTION_LATENCY = Histogram(
    "khive_reader_ingestion_latency_seconds",
    "Document ingestion latency in seconds"
)

PROCESSING_LATENCY = Histogram(
    "khive_reader_processing_latency_seconds",
    "Document processing latency in seconds"
)

PROCESSING_REQUESTS = Counter(
    "khive_reader_processing_requests_total",
    "Total number of document processing requests",
    ["status"]
)

VECTOR_COUNT = Gauge(
    "khive_reader_vector_count",
    "Total number of vectors stored"
)

DOCUMENT_COUNT = Gauge(
    "khive_reader_document_count",
    "Total number of documents stored"
)

CHUNK_SIZE_HISTOGRAM = Histogram(
    "khive_reader_chunk_size_bytes",
    "Size of document chunks in bytes",
    buckets=[100, 250, 500, 1000, 2500, 5000, 10000]
)

EMBEDDING_LATENCY = Histogram(
    "khive_reader_embedding_latency_seconds",
    "Time to generate embeddings in seconds"
)

TASK_QUEUE_SIZE = Gauge(
    "khive_reader_task_queue_size",
    "Number of tasks in the queue"
)

# Decorator for monitoring async functions
def monitor_async(metric_name, labels=None):
    """Decorator for monitoring async functions with Prometheus metrics."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            labels_dict = {}
            if labels:
                labels_dict = {k: kwargs.get(k, "unknown") for k in labels}
                
            start_time = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "failure"
                raise
            finally:
                duration = time.time() - start_time
                if metric_name == "search":
                    SEARCH_REQUESTS.labels(status=status, **labels_dict).inc()
                    SEARCH_LATENCY.observe(duration)
                elif metric_name == "ingestion":
                    INGESTION_REQUESTS.labels(status=status, **labels_dict).inc()
                    INGESTION_LATENCY.observe(duration)
                elif metric_name == "processing":
                    PROCESSING_REQUESTS.labels(status=status, **labels_dict).inc()
                    PROCESSING_LATENCY.observe(duration)
                elif metric_name == "embedding":
                    # Assuming embedding doesn't have status labels for now, adjust if needed
                    EMBEDDING_LATENCY.observe(duration)
        return wrapper
    return decorator

# Start Prometheus exporter
def start_metrics_server(port=8000):
    """Start Prometheus metrics server."""
    start_http_server(port)
    print(f"Prometheus metrics server started on port {port}")

# Background task to update metrics periodically
async def update_metrics_periodically(db_session_factory, task_queue):
    """Update metrics periodically in the background."""
    while True:
        try:
            # This part needs to be adapted based on actual DB and task queue implementation
            # For now, using placeholders as direct execution of SQL and len() might not be async
            # or might require specific library usage (e.g. SQLAlchemy async session)
            
            # Placeholder for DB interaction
            # async with db_session_factory() as session:
            #     # Update vector count
            #     result = await session.execute("SELECT COUNT(*) FROM document_chunks")
            #     vector_count = result.scalar()
            #     VECTOR_COUNT.set(vector_count)
                
            #     # Update document count
            #     result = await session.execute("SELECT COUNT(*) FROM documents")
            #     document_count = result.scalar()
            #     DOCUMENT_COUNT.set(document_count)
            
            # Placeholder for task queue interaction
            # TASK_QUEUE_SIZE.set(len(task_queue.pending_tasks))

            # Simulating some updates for now
            VECTOR_COUNT.set(0) # Replace with actual query
            DOCUMENT_COUNT.set(0) # Replace with actual query
            if hasattr(task_queue, 'qsize'): # Check if it's like asyncio.Queue
                 TASK_QUEUE_SIZE.set(task_queue.qsize())
            elif hasattr(task_queue, 'pending_tasks'): # Check for a custom attribute
                 TASK_QUEUE_SIZE.set(len(task_queue.pending_tasks))
            else:
                 TASK_QUEUE_SIZE.set(0) # Default if unknown structure

            print("Metrics updated (simulated DB/Queue)")

        except Exception as e:
            print(f"Error updating metrics: {e}")
        
        # Update every 60 seconds
        await asyncio.sleep(60)