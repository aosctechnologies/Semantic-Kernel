# plugins/queue_handler.py

from typing import List, Dict, Any
from datetime import datetime
from semantic_kernel.functions import kernel_function
from config.settings import settings
from services.http_client import get_client

class QueuePlugin:
    
    @kernel_function(
        name="process_items_queue",
        description="Process items sequentially and log results to MongoDB and Monitoring Agent."
    )
    async def process_items_queue(
        self,
        project_ids: List[str],
        workbook_ids: List[str],
        run_id: str,
        email: str  # Added to capture the user's email for logging
    ) -> List[Dict[str, Any]]:
        detailed_results = []
        log_lines = []
        
        if not project_ids or not workbook_ids:
            return [{"error": "Missing ID lists"}]

        async with await get_client() as client:
            for i, (pid, wid) in enumerate(zip(project_ids, workbook_ids)):
                project_status = {
                    "project_id": pid,
                    "workbook_id": wid,
                    "steps": {"assessment": "PENDING", "parsing": "SKIPPED", "mapping": "SKIPPED"},
                    "final_status": "PENDING"
                }
                
                file_label = f"file {i+1} ({pid})"
                current_chain = [file_label]

                # Step 1: Assessment - Only pid, wid, and run_id are passed
                try:
                    res = await client.post(
                        f"{settings.ASSESSMENT_API_URL}/api/assessment", 
                        json={"project_id": pid, "workbook_id": wid, "run_id": run_id}
                    )
                    res.raise_for_status()
                    project_status["steps"]["assessment"] = "COMPLETED"
                    current_chain.append("assessment pass")
                    
                    # Step 2: Parsing - Only pid, wid, and run_id are passed
                    try:
                        res = await client.post(
                            f"{settings.PARSING_API_URL}/parse-xml", 
                            json={"project_id": pid, "workbook_id": wid, "run_id": run_id}
                        )
                        res.raise_for_status()
                        project_status["steps"]["parsing"] = "COMPLETED"
                        current_chain.append("parsing pass")

                        # Step 3: Mapping - Only pid, wid, and run_id are passed
                        try:
                            res = await client.post(
                                f"{settings.MAPPING_API_URL}/mapping", 
                                json={"project_id": pid, "workbook_id": wid, "run_id": run_id}
                            )
                            res.raise_for_status()
                            project_status["steps"]["mapping"] = "COMPLETED"
                            project_status["final_status"] = "SUCCESS"
                            current_chain.append("mapping pass")
                        except Exception as e:
                            project_status["final_status"] = "WARNING"
                            current_chain.append(f"mapping error: {str(e)}")

                    except Exception as e:
                        project_status["final_status"] = "FAILED"
                        current_chain.append(f"parsing error: {str(e)}")

                except Exception as e:
                    project_status["final_status"] = "FAILED"
                    current_chain.append(f"assessment error: {str(e)}")

                detailed_results.append(project_status)
                log_lines.append(" -> ".join(current_chain))

                # --- NOTIFY MONITORING AGENT FOR EACH ITEM ---
                try:
                    await client.post(
                        settings.MONITORING_AGENT_URL + "/monitor/report",
                        json={
                            "project_id": pid,
                            "workbook_id": wid,
                            "run_id": run_id,
                            "status": project_status["final_status"]
                        },
                        timeout=5.0
                    )
                except Exception as monitor_err:
                    print(f"Monitoring Agent notification failed for {pid}: {monitor_err}")

            # --- MONGODB LOGGING ---
            # The email is included HERE for storage, but not in the processing calls above
            final_log_content = "\n".join(log_lines)
            log_payload = {
                "project_name": "Semantic-Kernel-Agent",
                "run_id": run_id,
                "status": "completed", 
                "payload": {
                    "user_email": email,  # Store the email in the log payload
                    "full_console_output": final_log_content,
                    "processed_items": detailed_results,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            try:
                await client.post(
                    f"{settings.MONGODB_LOG_API_URL}/api/records/semantic-kernel", 
                    json=log_payload
                )
            except Exception as e:
                print(f"Critical Logging Error: {e}")

        return detailed_results