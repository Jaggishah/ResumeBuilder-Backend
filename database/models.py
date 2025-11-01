from beanie import Document, init_beanie, PydanticObjectId
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from bson import ObjectId
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from enum import Enum
import os
from config.variable import MONGODB_URI, DATABASE_NAME

class SubscriptionType(str, Enum):
    TRIAL = "trial"
    BASIC = "basic"
    PREMIUM = "premium"
    PRO = "pro"





class User(Document):
    """User collection for managing users and their resumes"""
    username: str = Field(..., unique=True, min_length=3, max_length=50)
    email: Optional[str] = Field(None, unique=True)
    
    # Password authentication
    password_hash: Optional[str] = None  # For email/password auth
    
    # Google OAuth fields
    google_id: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    last_login: Optional[datetime] = None
    
    # Subscription and credits
    subscription_type: SubscriptionType = Field(default=SubscriptionType.TRIAL)
    credits_remaining: int = Field(default=10)  # Start with 10 credits for trial
    credits_used: int = Field(default=0)
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None
    
    resume_ids: List[PydanticObjectId] = Field(default_factory=list)  # Track resume IDs
    resume_count: int = Field(default=0)  # Quick count reference
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Settings:
        name = "users"
        indexes = ["username", "email", "google_id"]  # Create indexes for faster queries
    
    async def add_resume(self, resume_id: ObjectId):
        """Add a resume ID to the user's list and increment count"""
        if resume_id not in self.resume_ids:
            self.resume_ids.append(resume_id)
            self.resume_count = len(self.resume_ids)
            self.updated_at = datetime.now()
            await self.save()
    
    async def remove_resume(self, resume_id: ObjectId):
        """Remove a resume ID from the user's list and decrement count"""
        if resume_id in self.resume_ids:
            self.resume_ids.remove(resume_id)
            self.resume_count = len(self.resume_ids)
            self.updated_at = datetime.now()
            await self.save()
    
    async def use_credit(self, amount: int = 1) -> bool:
        """Use credits and return True if successful, False if insufficient credits"""
        if self.credits_remaining >= amount:
            self.credits_remaining -= amount
            self.credits_used += amount
            self.updated_at = datetime.now()
            await self.save()
            return True
        return False
    
    def has_credits(self, amount: int = 1) -> bool:
        """Check if user has enough credits"""
        return self.credits_remaining >= amount
    
    async def add_credits(self, amount: int):
        """Add credits to user account"""
        self.credits_remaining += amount
        self.updated_at = datetime.now()
        await self.save()

class Resume(Document):
    user_id: PydanticObjectId = Field(..., description="Reference to User who owns this resume")
    title: Optional[str] = Field(None, description="Resume title/name")
    username: Optional[str] = None  # Keep for backward compatibility
    email: str  # Store email for reference
    json_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def set_json_data(self, data: Dict[str, Any]):
        """Set JSON data and update timestamp"""
        self.json_data = data
        self.updated_at = datetime.now()

    def get_json_data(self) -> Dict[str, Any]:
        """Get JSON data"""
        return self.json_data
    
    class Settings:
        name = "resumes"  # Collection name
        indexes = ["user_id", "email", "created_at"]

class Feedback(Document):
    """Feedback collection for storing user feedback"""
    user_id: PydanticObjectId = Field(..., description="Reference to User who submitted feedback")
    user_email: str = Field(..., description="Email of the user who submitted feedback")
    message: str = Field(..., description="Detailed feedback message")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = Field(None, description="When feedback was resolved")
    
    class Settings:
        name = "feedback"
        indexes = ["user_id"]



async def init_database():
    """Initialize MongoDB connection and Beanie"""
    client = AsyncIOMotorClient(MONGODB_URI)
    await init_beanie(
        database=client[DATABASE_NAME],
        document_models=[User, Resume, Feedback]
    )
    print(f"Connected to MongoDB: {DATABASE_NAME}")

# Dependency for getting database (not needed with Beanie, but keeping for consistency)
async def get_db():
    """Database dependency - not needed with Beanie but keeping for API consistency"""
    yield None