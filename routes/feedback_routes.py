from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, List, Optional
from database.models import Feedback, User
from dto.feedback_dto import FeedbackCreateRequest
from middleware.auth import get_current_user
from beanie import PydanticObjectId
from datetime import datetime

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

@router.post("/submit", response_model=Dict[str, Any])
async def submit_feedback(
    feedback_data: FeedbackCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Submit feedback from authenticated user
    """
    try:
        # Get user details
        user = await User.get(PydanticObjectId(current_user["user_id"]))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Create feedback document
        feedback = Feedback(
            user_id=PydanticObjectId(current_user["user_id"]),
            user_email=user.email,
            message=feedback_data.message
        )
        
        # Save to database
        await feedback.insert()
        
        return {
            "message": "Feedback submitted successfully",
            "feedback_id": str(feedback.id),
            "status": "submitted"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting feedback: {str(e)}"
        )

