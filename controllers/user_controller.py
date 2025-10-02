from fastapi import HTTPException
from database.models import Resume, User
from typing import Dict, Any, List

class UserController:
    """Controller for user-related operations"""
    
    async def create_or_get_user(self, username: str, email: str = None) -> User:
        """Create a new user or get existing user by username"""
        # Check if user already exists
        existing_user = await User.find_one(User.username == username)
        if existing_user:
            return existing_user
        
        # Create new user
        user = User(
            username=username,
            email=email
        )
        await user.insert()
        return user
    
    async def get_user_by_username(self, username: str) -> User:
        """Get user by username"""
        user = await User.find_one(User.username == username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    
    async def get_user_stats(self, username: str) -> Dict[str, Any]:
        """Get user statistics including resume count"""
        user = await self.get_user_by_username(username)
        
        # Get actual resume count from database (for verification)
        actual_count = await Resume.find(Resume.username == username).count()
        
        # Update count if it's out of sync
        if user.resume_count != actual_count:
            user.resume_count = actual_count
            user.resume_ids = [
                resume.id for resume in 
                await Resume.find(Resume.username == username).to_list()
            ]
            await user.save()
        
        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "resume_count": user.resume_count,
            "resume_ids": [str(rid) for rid in user.resume_ids],
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
    
    async def list_all_users(self) -> List[Dict[str, Any]]:
        """List all users with their resume counts"""
        users = await User.find_all().sort(-User.updated_at).to_list()
        
        return [
            {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "resume_count": user.resume_count,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
            for user in users
        ]