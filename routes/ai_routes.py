from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any
from dto.enhancement_dto import EnhanceRequest, EnhanceResponse
from controllers.enhancement_controller import AIController
from pathlib import Path
from middleware.auth import get_current_user
from database.models import User
from services.credit_manager import CreditManager

router = APIRouter(prefix="/api/ai", tags=["enhancement"])
ai_controller = AIController()

@router.post("/enhance", response_model=EnhanceResponse)
async def enhance_section(
    data: EnhanceRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Enhance a specific resume section using AI
    Requires authentication and consumes 1 credit
    """
    try:
        # Get user from database to check credits
        user = await User.get(current_user["user_id"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check and deduct credits
        await CreditManager.check_and_use_credits(user, "enhance")
        
        content = data.content
        section_name = data.section_name
        if not content or content.strip() == "":
            # Refund credits if request is invalid
            await CreditManager.refund_credits(user, "enhance")
            raise HTTPException(status_code=400, detail="Content is required")

        if not data.instructions:
            # Try to load a prompt from prompts/enhancement.txt (project-level or relative)
            prompts_file = Path(__file__).resolve().parents[1] / "prompts" / "enhancement.txt"
            if not prompts_file.exists():
                prompts_file = Path("prompts/enhancement.txt")

            try:
                instructions = prompts_file.read_text(encoding="utf-8").strip()
            except Exception:
                instructions = f"Enhance the following to be more professional and impactful"
        else:
            additional_instructions = ''
            prompts_file = Path(__file__).resolve().parents[1] / "prompts" / "withInstruction_enhancement.txt"
            if not prompts_file.exists():
                instructions = data.instructions
            else:
                try:
                    additional_instructions = prompts_file.read_text(encoding="utf-8").strip()
                    instructions = additional_instructions + "\n" + data.instructions
                except Exception:
                    instructions = data.instructions
        
        # Perform the enhancement
        result = await ai_controller.enhance_resume_section(section_name, content, instructions)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        # Refund credits if operation fails
        try:
            user = await User.get(current_user["user_id"])
            if user:
                await CreditManager.refund_credits(user, "enhance")
        except:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enhancement failed: {str(e)}"
        )

