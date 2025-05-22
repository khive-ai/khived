import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


class PerformanceThreshold:
    """Performance threshold definition and checking."""

    def __init__(
        self,
        name: str,
        description: str,
        threshold_value: float,
        check_function: Callable[..., Awaitable[float]],
        alert_handler: Callable[[str, str, float, float], Awaitable[None]] = None,
    ):
        """Initialize a performance threshold."""
        self.name = name
        self.description = description
        self.threshold_value = threshold_value
        self.check_function = check_function
        self.alert_handler = alert_handler
        self.last_checked_time = 0.0  # Renamed from last_checked for clarity
        self.last_value = 0.0
        self.exceeded = False

    async def check(self, **kwargs) -> bool:
        """Check if the threshold is exceeded."""
        try:
            current_time = time.time()
            value = await self.check_function(**kwargs)
            self.last_checked_time = current_time
            self.last_value = value

            if value > self.threshold_value:
                if not self.exceeded:  # Alert only on first exceed
                    self.exceeded = True
                    logger.warning(
                        f"Performance threshold EXCEEDED: {self.name} (Value: {value} > Threshold: {self.threshold_value})"
                    )
                    if self.alert_handler:
                        await self.alert_handler(
                            self.name, self.description, value, self.threshold_value
                        )
                return True  # Still return True if it's currently exceeded
            elif value <= self.threshold_value and self.exceeded:  # Recovered
                self.exceeded = False
                logger.info(
                    f"Performance threshold RECOVERED: {self.name} (Value: {value} <= Threshold: {self.threshold_value})"
                )

            return self.exceeded  # Return current state
        except Exception as e:
            logger.error(f"Error checking threshold {self.name}: {e}", exc_info=True)
            # Decide if an error in checking should count as exceeded or maintain last state.
            # For now, returning current 'exceeded' state to avoid flapping on transient check errors.
            return self.exceeded


class PerformanceMonitor:
    """Monitor for tracking performance thresholds."""

    def __init__(self, db_session_factory, task_queue):
        """Initialize the performance monitor."""
        self.db_session_factory = db_session_factory
        self.task_queue = task_queue
        self.thresholds: list[PerformanceThreshold] = []
        self._setup_thresholds()  # Renamed for convention

    def _setup_thresholds(self):
        """Set up performance thresholds."""
        # Default alert handler can be assigned here or passed during PerformanceThreshold instantiation
        default_alert_handler = self.default_alert_handler

        self.thresholds = [
            PerformanceThreshold(
                name="vector_count",
                description="Number of vectors in the database",
                threshold_value=5_000_000,  # 5 million vectors
                check_function=self._check_vector_count,
                alert_handler=default_alert_handler,
            ),
            PerformanceThreshold(
                name="search_latency_p95_ms",  # Clarified name
                description="p95 search latency in milliseconds",
                threshold_value=100,  # 100ms
                check_function=self._check_search_latency,
                alert_handler=default_alert_handler,
            ),
            PerformanceThreshold(
                name="task_queue_depth",
                description="Number of pending tasks in the queue",
                threshold_value=1000,  # 1000 tasks
                check_function=self._check_task_queue_depth,
                alert_handler=default_alert_handler,
            ),
            PerformanceThreshold(
                name="db_connection_utilization_percent",  # Clarified name
                description="Database connection pool utilization (0.0 to 1.0)",
                threshold_value=0.9,  # 90%
                check_function=self._check_db_connection_utilization,
                alert_handler=default_alert_handler,
            ),
        ]

    async def _check_vector_count(
        self, **kwargs
    ) -> float:  # Added **kwargs to match signature
        """Check the total number of vectors in the database."""
        # This needs actual async DB interaction. Placeholder for now.
        # Example with a hypothetical async session:
        # async with self.db_session_factory() as session:
        #     result = await session.execute("SELECT COUNT(*) FROM document_chunks")
        #     return float(result.scalar_one_or_none() or 0)
        logger.debug("Checking vector count (placeholder)")
        return 0.0  # Placeholder

    async def _check_search_latency(self, **kwargs) -> float:  # Added **kwargs
        """Calculate the p95 search latency from metrics."""
        # In a real implementation, this would query a time-series DB (e.g., Prometheus)
        # or access histogram data directly if available in memory.
        # For now, just return a placeholder
        logger.debug("Checking search latency (placeholder)")
        return 50.0  # Placeholder value in ms

    async def _check_task_queue_depth(self, **kwargs) -> float:  # Added **kwargs
        """Check the number of pending tasks in the queue."""
        logger.debug("Checking task queue depth")
        if hasattr(self.task_queue, "qsize"):  # For asyncio.Queue
            return float(self.task_queue.qsize())
        elif hasattr(self.task_queue, "pending_tasks"):  # For custom queue
            return float(len(self.task_queue.pending_tasks))
        logger.warning("Task queue structure not recognized for depth check.")
        return 0.0  # Placeholder

    async def _check_db_connection_utilization(
        self, **kwargs
    ) -> float:  # Added **kwargs
        """Check database connection pool utilization."""
        # This is a placeholder - in a real impl, we'd query the connection pool metrics
        logger.debug("Checking DB connection utilization (placeholder)")
        return 0.5  # Placeholder value (50%)

    async def default_alert_handler(
        self, name: str, description: str, value: float, threshold: float
    ):
        """Handle threshold alerts by logging."""
        try:
            exceeded_by_percentage = (
                ((value / threshold) - 1) * 100 if threshold > 0 else float("inf")
            )
        except ZeroDivisionError:
            exceeded_by_percentage = float("inf")

        alert_message = f"""
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        PERFORMANCE THRESHOLD EXCEEDED
        ----------------------------------
        Threshold Name: {name}
        Description:    {description}
        Current Value:  {value:.2f}
        Threshold:      {threshold:.2f}
        Exceeded by:    {exceeded_by_percentage:.1f}%
        Timestamp:      {time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime())}
        ----------------------------------
        Recommended Action: Investigate the '{name}' metric. Consider system scaling or component optimization.
        If this pertains to resource limits (e.g., vector count, queue depth),
        it might indicate a need to scale resources or extract the related component into a separate microservice.
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        logger.warning(alert_message)
        # In a production environment, this could integrate with PagerDuty, Slack, Email, etc.

    async def check_all_thresholds(self) -> dict[str, Any]:
        """Check all performance thresholds and return their status."""
        results = {}
        logger.info("Checking all performance thresholds...")
        for threshold in self.thresholds:
            # Pass along db_session_factory and task_queue if needed by check_function
            # The current check_functions in this class use self.db_session_factory etc.
            # but if check_function was external, it would need them passed.
            # For now, the **kwargs in threshold.check() is not strictly used by internal checks.
            await threshold.check()
            results[threshold.name] = {
                "exceeded": threshold.exceeded,
                "current_value": threshold.last_value,
                "threshold_value": threshold.threshold_value,
                "last_checked_timestamp": threshold.last_checked_time,  # Changed key name
            }
            logger.debug(
                f"Threshold '{threshold.name}': Value={threshold.last_value}, Exceeded={threshold.exceeded}"
            )
        logger.info("Finished checking all performance thresholds.")
        return results

    async def monitor_periodically(self, interval_seconds: int = 300):
        """Monitor thresholds periodically in the background."""
        logger.info(
            f"Performance monitor starting periodic checks every {interval_seconds} seconds."
        )
        while True:
            try:
                await self.check_all_thresholds()
            except Exception as e:
                logger.error(
                    f"Error during periodic threshold check: {e}", exc_info=True
                )
            await asyncio.sleep(interval_seconds)
