from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from bson import ObjectId

class ResumeDTO(BaseModel):
    id: Optional[str] = None
    username: Optional[str] = None
    json_data: Dict[str, Any] = Field(default_factory=dict)
    yaml_content: Optional[str] = None
    pdf_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    email: Optional[EmailStr] = None

    @field_validator('id', mode='before')
    @classmethod
    def convert_objectid_to_string(cls, v):
        """Convert ObjectId to string"""
        if isinstance(v, ObjectId):
            return str(v)
        return v

    class Config:
        # Allow arbitrary types (like ObjectId) during processing
        arbitrary_types_allowed = True
        # Convert to JSON serializable types
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

class ResumeGenerateDTO(BaseModel):
    id: Optional[str] = None
    pdf_path: Optional[str] = None
    yaml_path: Optional[str] = None
    message: Optional[str] = None