from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ImageGenerationRequest(BaseModel):
    prompts: List[str]
    model: str
    project_id: str
    style_overrides: Optional[Dict[str, Any]] = None

class VideoGenerationRequest(BaseModel):
    prompts: List[str]
    model: str
    project_id: str
    reference_images: Optional[List[str]] = None

class VisionQCRequest(BaseModel):
    image_urls: List[str]
    project_id: str
    criteria: Optional[Dict[str, Any]] = None

# Using generic dict for schema outputs to avoid verbose nested classes for stubs
class VisionQCResponse(BaseModel):
    scores: Dict[str, Dict[str, Any]] # Output map of image_url to scores

class StorageRequest(BaseModel):
    files: List[str]
    project_id: str
    subfolder: str
