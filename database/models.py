from beanie import Document, init_beanie, PydanticObjectId
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from bson import ObjectId
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import os


class User(Document):
    """User collection for managing users and their resumes"""
    username: str = Field(..., unique=True, min_length=3, max_length=50)
    email: Optional[str] = None
    resume_ids: List[PydanticObjectId] = Field(default_factory=list)  # Track resume IDs
    resume_count: int = Field(default=0)  # Quick count reference
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "users"
        indexes = ["username"]  # Create index on username for faster queries
    
    async def add_resume(self, resume_id: ObjectId):
        """Add a resume ID to the user's list and increment count"""
        if resume_id not in self.resume_ids:
            self.resume_ids.append(resume_id)
            self.resume_count = len(self.resume_ids)
            self.updated_at = datetime.utcnow()
            await self.save()
    
    async def remove_resume(self, resume_id: ObjectId):
        """Remove a resume ID from the user's list and decrement count"""
        if resume_id in self.resume_ids:
            self.resume_ids.remove(resume_id)
            self.resume_count = len(self.resume_ids)
            self.updated_at = datetime.utcnow()
            await self.save()

class Resume(Document):
    username: Optional[str] = None
    json_data: Dict[str, Any] = Field(default_factory=dict)
    yaml_content: Optional[str] = None
    pdf_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def set_json_data(self, data: Dict[str, Any]):
        """Set JSON data and update timestamp"""
        self.json_data = data
        self.updated_at = datetime.utcnow()
    
    def get_json_data(self) -> Dict[str, Any]:
        """Get JSON data"""
        return self.json_data
    
    class Settings:
        name = "resumes"  # Collection name
        indexes = ["user", "created_at"]

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "resume_builder")

async def init_database():
    """Initialize MongoDB connection and Beanie"""
    client = AsyncIOMotorClient(MONGODB_URL)
    await init_beanie(
        database=client[DATABASE_NAME],
        document_models=[User,Resume]
    )
    print(f"Connected to MongoDB: {DATABASE_NAME}")

# Dependency for getting database (not needed with Beanie, but keeping for consistency)
async def get_db():
    """Database dependency - not needed with Beanie but keeping for API consistency"""
    yield None