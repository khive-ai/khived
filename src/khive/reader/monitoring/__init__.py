import asyncio
import logging

from khive.reader.monitoring.prometheus import (
    start_metrics_server,
    update_metrics_periodically,
)
from khive.reader.monitoring.thresholds import PerformanceMonitor

# Attempt to import DB and task queue; provide fallbacks if not found
# This allows the monitoring module to be imported even if other parts are not fully set up.
try:
    from khive.reader.db import get_db_session  # type: ignore
except ImportError:
    logging.warning(
        "khive.reader.db.get_db_session not found. Monitoring DB-dependent features will use placeholders."
    )

    async def get_db_session():  # Placeholder
        logging.debug("Using placeholder get_db_session for monitoring.")

        class MockAsyncSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

            async def execute(self, stmt):
                class MockResult:
                    def scalar(self):
                        return 0

                    def scalar_one_or_none(self):
                        return 0

                return MockResult()

        return MockAsyncSession()


try:
    from khive.reader.tasks.queue import task_queue  # type: ignore
except ImportError:
    logging.warning(
        "khive.reader.tasks.queue.task_queue not found. Monitoring task queue dependent features will use placeholders."
    )

    class MockTaskQueue:  # Placeholder
        def __init__(self):
            self.pending_tasks = []
            logging.debug("Using placeholder task_queue for monitoring.")

        def qsize(self):  # if it mimics asyncio.Queue
            return len(self.pending_tasks)

    task_queue = MockTaskQueue()


logger = logging.getLogger(__name__)


def start_monitoring(prometheus_port: int = 8000):
    """
    Start all monitoring components.
    Returns the initialized PerformanceMonitor instance.
    """
    logger.info(
        f"Initializing monitoring components. Prometheus port: {prometheus_port}"
    )

    # Start Prometheus metrics server
    try:
        start_metrics_server(port=prometheus_port)
        logger.info(
            f"Prometheus metrics server started successfully on port {prometheus_port}."
        )
    except Exception as e:
        logger.error(
            f"Failed to start Prometheus metrics server on port {prometheus_port}: {e}",
            exc_info=True,
        )
        # Depending on policy, we might want to raise this or allow app to continue without metrics server

    # Start background tasks for updating metrics
    try:
        asyncio.create_task(update_metrics_periodically(get_db_session, task_queue))
        logger.info("Background task for periodic Prometheus metric updates scheduled.")
    except Exception as e:
        logger.error(
            f"Failed to schedule periodic Prometheus metric updates: {e}", exc_info=True
        )

    # Initialize performance monitor
    performance_monitor = None
    try:
        performance_monitor = PerformanceMonitor(get_db_session, task_queue)
        logger.info("PerformanceMonitor initialized.")

        # Start periodic monitoring by the performance monitor
        asyncio.create_task(performance_monitor.monitor_periodically())
        logger.info(
            "Background task for periodic performance threshold monitoring scheduled."
        )
    except Exception as e:
        logger.error(
            f"Failed to initialize or schedule PerformanceMonitor: {e}", exc_info=True
        )
        # If performance_monitor failed to init, return None or a dummy
        if performance_monitor is None:

            class DummyPerformanceMonitor:  # So the return type is consistent
                async def check_all_thresholds(self):
                    return {}

                async def monitor_periodically(self, interval_seconds: int = 300):
                    pass

            performance_monitor = DummyPerformanceMonitor()

    logger.info("Monitoring components initialization process completed.")
    return performance_monitor
