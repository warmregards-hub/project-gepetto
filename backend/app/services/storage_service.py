import os
from pathlib import Path
from app.config import settings

class StorageService:
    def __init__(self):
        self.base_path = Path(settings.storage_path)

    async def save_file(self, content: bytes, project_id: str, subfolder: str, filename: str) -> str:
        """Saves file to /storage/[client]/[subfolder]/..."""
        project_dir = self.base_path / project_id / subfolder
        project_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = project_dir / filename
        with open(file_path, "wb") as f:
            f.write(content)
            
        print(f"[Project Gepetto Storage] Saved file to {file_path}")
        return str(file_path)
