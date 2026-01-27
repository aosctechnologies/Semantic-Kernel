# plugins/monitoring_agent.py

from semantic_kernel.functions import kernel_function
from services.http_client import get_client
from config.settings import settings # Import settings
import httpx

class MonitoringAgentPlugin:
    
    @kernel_function(
        name="report_to_monitor",
        description="Sends a status report to the external monitoring agent."
    )
    async def report_to_monitor(
        self,
        project_id: str,
        workbook_id: str,
        run_id: str,
        status: str = "PROCESSED"
    ) -> str:
        # Use the URL from the .env via settings
        url = settings.MONITORING_AGENT_URL + "/monitor/report"
        
        payload = {
            "project_id": project_id,
            "workbook_id": workbook_id,
            "run_id": run_id,
            "status": status
        }

        try:
            async with await get_client() as client:
                response = await client.post(
                    url,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                return f"Monitoring Agent notified for Run {run_id}"
        except Exception as e:
            return f"Monitoring Agent Error: {str(e)}"