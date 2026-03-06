from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/callback")
async def n8n_webhook_callback(request: Request):
    """
    Receives callbacks from n8n webhooks. 
    POST /api/n8n/callback with job_id, status (completed/failed/partial), outputs array, errors array, processing_time_seconds.
    """
    payload = await request.json()
    print(f"[Project Gepetto] Received n8n callback: {payload}")
    return {"status": "received"}
