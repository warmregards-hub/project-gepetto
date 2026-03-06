class N8nClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def trigger_workflow(self, workflow_name: str, payload: dict):
        # e.g., POST to {base_url}/webhook/{workflow_name}
        print(f"[Project Gepetto N8N] Triggering {workflow_name} with {payload}")
        return {"status": "triggered", "workflow": workflow_name}
