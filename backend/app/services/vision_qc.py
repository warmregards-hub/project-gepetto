import random
import asyncio
from app.config import settings

class VisionQCService:
    async def score_image(self, image_url: str, project_id: str, criteria: dict = None):
        if settings.mock_generation:
            # Mock mode: return random decent score
            await asyncio.sleep(0.5)
            score = round(random.uniform(7.0, 9.5), 1)
            print(f"[Project Gepetto Vision QC] MOCK Scoring {image_url}: {score}/10")
            return {
                "composition": score,
                "clarity": score,
                "prompt_adherence": score,
                "style_match": score,
                "overall": score,
                "reason": "Mocked QC evaluation complete."
            }
            
        # Phase 2 actual implementation logic (using claude-3.5-sonnet via Kie.ai vision)
        return {
            "composition": 9.0,
            "clarity": 8.5,
            "prompt_adherence": 9.5,
            "style_match": 8.0,
            "overall": 8.75,
            "reason": "Actual vision API not yet hooked up."
        }
