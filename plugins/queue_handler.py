# plugins/queue_handler.py

from typing import List, Dict, Any
from datetime import datetime
from semantic_kernel.functions import kernel_function
from config.settings import settings
from services.http_client import get_client

class QueuePlugin:
    
    @kernel_function(
        name="process_items_queue",
        description="Process a list of items sequentially and log structured results for every file."
    )
    async def process_items_queue(
        self,
        project_ids: List[str],
        workbook_ids: List[str],
        run_id: str
    ) -> List[Dict[str, Any]]:
        detailed_results = []
        log_lines = []
        
        # Guard against empty input
        if not project_ids or not workbook_ids:
            return [{"error": "Missing ID lists"}]

        async with await get_client() as client:
            # Enumerate allows us to track "file 1", "file 2", etc.
            for i, (pid, wid) in enumerate(zip(project_ids, workbook_ids)):
                project_status = {
                    "project_id": pid,
                    "workbook_id": wid,
                    "steps": {"assessment": "PENDING", "parsing": "SKIPPED", "mapping": "SKIPPED"},
                    "final_status": "PENDING"
                }
                
                # Start the detailed chain for this specific file
                file_label = f"file {i+1} ({pid})"
                current_chain = [file_label]

                # --- STEP 1: ASSESSMENT ---
                try:
                    res = await client.post(
                        f"{settings.ASSESSMENT_API_URL}/api/assessment", 
                        json={"project_id": pid, "workbook_id": wid, "run_id": run_id},
                        timeout=60.0
                    )
                    res.raise_for_status()
                    project_status["steps"]["assessment"] = "COMPLETED"
                    current_chain.append("assessment pass")
                    
                    # --- STEP 2: PARSING ---
                    try:
                        res = await client.post(
                            f"{settings.PARSING_API_URL}/parse-xml", 
                            json={"project_id": pid, "workbook_id": wid, "run_id": run_id},
                            timeout=60.0
                        )
                        res.raise_for_status()
                        project_status["steps"]["parsing"] = "COMPLETED"
                        current_chain.append("parsing pass")

                        # --- STEP 3: MAPPING ---
                        try:
                            res = await client.post(
                                f"{settings.MAPPING_API_URL}/mapping", 
                                json={"project_id": pid, "workbook_id": wid, "run_id": run_id},
                                timeout=60.0
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
                # Combine the chain for this file (e.g., "file 1 -> assessment pass -> ...")
                log_lines.append(" -> ".join(current_chain))

            # --- CONSTRUCT FINAL LOG FOR MONGODB ---
            final_log_content = "\n".join(log_lines)

            log_payload = {
                "project_name": "Batch Process",
                "run_id": run_id,
                "agent_name": "Semantic Kernel Queue Agent",
                "log_level": "INFO",
                "message": f"Processed {len(project_ids)} files",
                "details": {
                    "log_content": final_log_content,
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "COMPLETED"
                }
            }
            
            try:
                # Log to the specific /logs endpoint
                await client.post(f"{settings.MONGODB_LOG_API_URL}/api/records/logs", json=log_payload)
            except Exception as e:
                print(f"Logging Error: {e}")

        return detailed_results

    