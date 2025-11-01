from fastapi import APIRouter, UploadFile, File, Query, Form, Depends, HTTPException, status
from typing import Dict, Any, List, Optional
from controllers.resume_controller import ResumeController
from dto import (
    ResumeDTO, ResumeGenerateDTO
)
from middleware.auth import get_current_user
from database.models import Resume, User
from pydantic import BaseModel
from beanie import PydanticObjectId
from datetime import datetime
router = APIRouter(prefix="/api/resumes", tags=["resumes"])
resume_controller = ResumeController()

# Pydantic models for new authenticated routes
class SaveResumeRequest(BaseModel):
    title: Optional[str] = None
    json_data: Dict[str, Any]

class ResumeResponse(BaseModel):
    id: str
    title: Optional[str]
    json_data: Dict[str, Any]
    created_at: str
    updated_at: str

@router.post("/upload",response_model=ResumeDTO)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Upload and parse a resume PDF
    Requires authentication - uses authenticated user's info
    """
    # Get user info from database
    user = await User.get(current_user["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Use authenticated user's username and email
    return await resume_controller.upload_and_parse_resume(
        file, 
        username=user.username, 
        email=user.email,
        user_id=current_user["user_id"]
    )

@router.post("/analyze")
async def analyze_ats(
    resume_file: Optional[UploadFile] = File(None, description="Resume PDF file"),
    resume_text: Optional[str] = Form(None, description="Resume text content"),
    job_description: Optional[str] = Form(None, description="Job description text"),
    job_url: Optional[str] = Form(None, description="Job posting URL")
):
    """Analyze resume against job requirements for ATS compatibility"""
    return await resume_controller.analyze_ats_compatibility(
        resume_file=resume_file,
        resume_text=resume_text,
        job_description=job_description,
        job_url=job_url
    )



# New authenticated routes
@router.post("/save", response_model=ResumeResponse)
async def save_resume(
    request: SaveResumeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Save a new resume for the authenticated user
    Requires Authorization header with Bearer token
    """
    
    try:
        # Get user to update their resume count
        user = await User.get(current_user["user_id"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        print(user)
        # Create new resume
        new_resume = Resume(
            user_id=PydanticObjectId(current_user["user_id"]),
            title=request.title or f"Resume {user.resume_count + 1}",
            email=current_user["email"],
            username=user.username,
            json_data=request.json_data,
        )
        # Save resume
        await new_resume.insert()
        
        # Update user's resume count and list
        await user.add_resume(new_resume.id)
        
        return ResumeResponse(
            id=str(new_resume.id),
            title=new_resume.title,
            json_data=new_resume.json_data,
            created_at=new_resume.created_at.isoformat(),
            updated_at=new_resume.updated_at.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving resume: {str(e)}"
        )

@router.get("/my-resumes", response_model=List[ResumeResponse])
async def get_my_resumes(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get all resumes for the authenticated user
    Requires Authorization header with Bearer token
    """
    try:
        # Find all resumes for the current user
        resumes = await Resume.find(Resume.user_id == PydanticObjectId(current_user["user_id"])).to_list()
        
        # Convert to response format
        resume_list = []
        for resume in resumes:
            resume_list.append(ResumeResponse(
                id=str(resume.id),
                title=resume.title,
                json_data=resume.json_data,
                created_at=resume.created_at.isoformat(),
                updated_at=resume.updated_at.isoformat()
            ))
        
        return resume_list
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching resumes: {str(e)}"
        )

@router.get("/my-resumes-id/{resume_id}", response_model=ResumeResponse)
async def get_my_resume_by_id(
    resume_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a specific resume by ID for the authenticated user
    Requires Authorization header with Bearer token
    """
    try:
        # Verify the resume belongs to the current user
        resume = await Resume.find_one(
            Resume.id == PydanticObjectId(resume_id),
            Resume.user_id == PydanticObjectId(current_user["user_id"])
        )
        
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found or access denied"
            )
        
        return ResumeResponse(
            id=str(resume.id),
            title=resume.title,
            json_data=resume.json_data,
            created_at=resume.created_at.isoformat(),
            updated_at=resume.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching resume: {str(e)}"
        )

@router.put("/my-resumes-id/{resume_id}", response_model=ResumeResponse)
async def update_my_resume(
    resume_id: str,
    request: SaveResumeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update a specific resume for the authenticated user
    Requires Authorization header with Bearer token
    """
    try:
        # Verify the resume belongs to the current user
        resume = await Resume.find_one(
            Resume.id == PydanticObjectId(resume_id),
            Resume.user_id == PydanticObjectId(current_user["user_id"])
        )
        
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found or access denied"
            )
        
        # Update resume fields
        if request.title is not None:
            resume.title = request.title
        resume.json_data = request.json_data
        if request.yaml_content is not None:
            resume.yaml_content = request.yaml_content
        resume.updated_at = resume.updated_at
        
        # Save changes
        await resume.save()
        
        return ResumeResponse(
            id=str(resume.id),
            title=resume.title,
            json_data=resume.json_data,
            yaml_content=resume.yaml_content,
            pdf_path=resume.pdf_path,
            created_at=resume.created_at.isoformat(),
            updated_at=resume.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating resume: {str(e)}"
        )

@router.delete("/my-resumes-id/{resume_id}")
async def delete_my_resume(
    resume_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a specific resume for the authenticated user
    Requires Authorization header with Bearer token
    """
    try:
        # Verify the resume belongs to the current user
        resume = await Resume.find_one(
            Resume.id == PydanticObjectId(resume_id),
            Resume.user_id == PydanticObjectId(current_user["user_id"])
        )
        
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found or access denied"
            )
        
        # Remove from user's resume list
        user = await User.get(current_user["user_id"])
        if user:
            await user.remove_resume(resume.id)
        
        # Delete the resume
        await resume.delete()
        
        return {"message": "Resume deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting resume: {str(e)}"
        )