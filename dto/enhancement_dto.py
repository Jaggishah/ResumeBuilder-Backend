from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime


class EnhanceRequest(BaseModel):
    content: str
    section_name : str



class EnhanceResponse(BaseModel):
    section: str
    original: str
    enhanced: str

