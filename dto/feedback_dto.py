from pydantic import BaseModel, Field


class FeedbackCreateRequest(BaseModel):
    """Request model for creating feedback"""
    message: str = Field(..., description="Detailed feedback message")

    

