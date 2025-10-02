from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from dto.enhancement_dto import EnhanceRequest, EnhanceResponse
from controllers.enhancement_controller import AIController
from pathlib import Path

router = APIRouter(prefix="/api/ai", tags=["enhancement"])
ai_controller = AIController()

@router.post("/enhance", response_model=EnhanceResponse)
async def enhance_section(
    data: EnhanceRequest
):
    """Enhance a specific resume section using AI"""
    content = data.content
    section_name = data.section_name
    if not content or content.strip() == "":
        raise HTTPException(status_code=400, detail="Content is required")

   
    # Try to load a prompt from prompts/enhancement.txt (project-level or relative)
    prompts_file = Path(__file__).resolve().parents[1] / "prompts" / "enhancement.txt"
    if not prompts_file.exists():
        prompts_file = Path("prompts/enhancement.txt")

    try:
        instructions = prompts_file.read_text(encoding="utf-8").strip()
    except Exception:
        instructions = f"Enhance the following  to be more professional and impactful"
    return await ai_controller.enhance_resume_section(section_name, content, instructions)

