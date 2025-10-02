from fastapi import HTTPException, UploadFile
from typing import Dict, Any, List
import uuid
import os
from pathlib import Path
import json
from bson import ObjectId
from beanie import PydanticObjectId
from services import parser, agent, yaml_converter, rendercvAgent
from database.models import Resume
from controllers.user_controller import UserController

class ResumeController:
    def __init__(self):
        self.parser_instance = parser.PDFResumeParser()
        self.agent_instance = agent.ResumeAgent()
        self.user_controller = UserController()
        self.rendercv_agent = rendercvAgent.RenderCVAgent()

    async def upload_and_parse_resume(self, file: UploadFile, username: str, email: str = None) -> Dict[str, Any]:
        """Handle resume upload and parsing"""

        user = await self.user_controller.create_or_get_user(username, email=email)
        # Save uploaded file temporarily
        temp_path = f"temp_{uuid.uuid4()}.pdf"
        try:
            with open(temp_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # Parse PDF content
            text_content = self.parser_instance.extract_raw_text(temp_path)
            
            if not text_content:
                raise HTTPException(status_code=400, detail="Could not extract text from PDF")
            
            # Get AI-parsed JSON
            instructions_path = Path(__file__).parent.parent / "prompts" / "instructions.txt"
            instructions = instructions_path.read_text(encoding="utf-8")
            
            json_content = await self.agent_instance.process_resume(
                current_content=text_content, 
                instructions=instructions
            )
            
            # Parse and validate JSON
            try:
                parsed_data = json.loads(json_content)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Failed to parse AI response")
            
            # Create new resume entry in MongoDB
            resume = Resume(
                username=user.username,
                email=user.email,
                json_data=parsed_data
            )
            
            await resume.insert()
            await user.add_resume(resume.id)
            return resume
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    async def get_resume_by_id(self, resume_id: str) -> Dict[str, Any]:
        """Get resume data by ID"""
        try:
            resume = await Resume.get(PydanticObjectId(resume_id))
        except:
            raise HTTPException(status_code=400, detail="Invalid resume ID")
            
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        return resume
    
    async def update_resume_data(self, resume_id: str, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update resume data"""
        try:
            resume = await Resume.get(ObjectId(resume_id))
        except:
            raise HTTPException(status_code=400, detail="Invalid resume ID")
            
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        resume.set_json_data(resume_data)
        await resume.save()
        
        return resume
        
    
    async def list_all_resumes(self) -> List[Dict[str, Any]]:
        """List all resumes"""
        resumes = await Resume.find_all().sort(-Resume.updated_at).to_list()
        return [
            r
            for r in resumes
        ]
    
    async def generate_pdf_from_resume(self, resume_id: str) -> Dict[str, Any]:
        """Generate PDF from resume data"""
        try:
            resume = await Resume.get(ObjectId(resume_id))
        except:
            raise HTTPException(status_code=400, detail="Invalid resume ID")
            
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        try:
            # Convert to YAML
            yaml_content = yaml_converter.convert_to_rendercv(resume.get_json_data())
            
            # Save YAML file
            yaml_path = f"resume_{resume_id}.yaml"
            with open(yaml_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)
            
            # Generate PDF using async function
            pdf_path = f"resume_{resume_id}.pdf"
       
            success = await self.rendercv_agent.create_pdf_with_rendercv(yaml_path, pdf_path)
            
            if success:
                # Update resume with paths
                resume.yaml_content = yaml_content
                resume.pdf_path = pdf_path
                await resume.save()
                
                return {
                    "id": str(resume.id),
                    "pdf_path": pdf_path,
                    "yaml_path": yaml_path,
                    "message": "PDF generated successfully"
                }
            else:
                raise HTTPException(status_code=500, detail="PDF generation failed")
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")


