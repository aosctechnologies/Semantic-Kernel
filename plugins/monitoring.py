# plugins/monitoring.py

from semantic_kernel.functions import kernel_function
from config.settings import settings
from services.http_client import get_client
from datetime import datetime

class MonitoringPlugin:
    
    @kernel_function(
        name="log_event",
        description="Logs a specific agent event or performance metric to the monitoring API."
    )
    async def log_event(
        self,
        event_name: str,
        run_id: str,
        details: str = ""
    ) -> str:
        """
        Sends a monitoring event to the MongoDB/Logging service.
        """
        payload = {
            "run_id": run_id,
            "event": event_name,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details,
            "type": "MONITORING_LOG"
        }

        try:
            async with await get_client() as client:
                # Reusing your MONGODB_LOG_API_URL from settings
                response = await client.post(
                    f"{settings.MONGODB_LOG_API_URL}/api/records/monitoring",
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                return f"Monitoring Log Success: {event_name}"
        except Exception as e:
            return f"Monitoring Log Failed: {str(e)}"

    @kernel_function(
        name="get_run_status",
        description="Checks the current status of a specific batch run."
    )
    async def get_run_status(self, run_id: str) -> str:
        try:
            async with await get_client() as client:
                response = await client.get(
                    f"{settings.MONGODB_LOG_API_URL}/api/records/validation/{run_id}",
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                return f"Run {run_id} status: {data.get('status', 'Unknown')}"
        except Exception as e:
            return f"Status Check Failed: {str(e)}"