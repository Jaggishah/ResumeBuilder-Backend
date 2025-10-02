from fastapi import APIRouter, UploadFile, File, Query
from typing import Dict, Any, List,Optional
from controllers.resume_controller import ResumeController
from dto import (
    ResumeDTO, ResumeGenerateDTO
)
router = APIRouter(prefix="/api/resumes", tags=["resumes"])
resume_controller = ResumeController()

@router.post("/upload",response_model=ResumeDTO)
async def upload_resume(file: UploadFile = File(...),
    username: str = Query(..., description="Username to associate with the resume"),
    email: str = Query(..., description="Email address of the user")
    
    ):
    """Upload and parse a resume PDF"""
    return await resume_controller.upload_and_parse_resume(file, username, email=email)

@router.get("/{resume_id}",response_model=ResumeDTO)
async def get_resume(resume_id: str):
    """Get resume data by ID"""
    return await resume_controller.get_resume_by_id(resume_id)

@router.put("/{resume_id}", response_model=ResumeDTO)
async def update_resume(resume_id: str, resume_data: Dict[str, Any]):
    """Update resume data"""
    return await resume_controller.update_resume_data(resume_id, resume_data)

@router.get("/",response_model=List[ResumeDTO])
async def list_resumes():
    """List all resumes"""
    return await resume_controller.list_all_resumes()

@router.post("/{resume_id}/generate-pdf",response_model=ResumeGenerateDTO)
async def generate_pdf(resume_id: str):
    """Generate PDF from resume data"""
    return await resume_controller.generate_pdf_from_resume(resume_id)