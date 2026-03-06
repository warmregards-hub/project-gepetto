import os
import zipfile
import io
import urllib.parse
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from app.api.deps import get_current_user
from app.config import settings
import httpx

router = APIRouter()

@router.get("/download/{project_id}/{subfolder}/{filename}")
async def download_file(
    project_id: str,
    subfolder: str,
    filename: str,
):
    """Serve stored files. No auth required — browser img tags can't send JWT headers."""
    file_path = Path(settings.storage_path) / project_id / subfolder / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(path=file_path, filename=filename)

@router.get("/proxy")
async def proxy_image(
    url: str,
    current_user: str = Depends(get_current_user)
):
    """Proxy an external image URL through the backend (handles authenticated Kie.ai CDN URLs)."""
    decoded_url = urllib.parse.unquote(url)
    headers = {"Authorization": f"Bearer {settings.kie_api_key}"}
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(decoded_url, headers=headers)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/jpeg")
            return StreamingResponse(
                io.BytesIO(resp.content),
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=3600"}
            )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to proxy image: {str(e)}")

@router.get("/download_zip/{project_id}/{subfolder}")
async def download_zip(
    project_id: str,
    subfolder: str,
    current_user: str = Depends(get_current_user)
):
    directory_path = Path(settings.storage_path) / project_id / subfolder
    if not directory_path.exists() or not directory_path.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, _, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, directory_path)
                zip_file.write(file_path, arcname)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={project_id}_{subfolder}.zip"}
    )
