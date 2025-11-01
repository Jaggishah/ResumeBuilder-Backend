from fastapi import HTTPException
from typing import Dict, Any
from services import  agent, groq_agent


class AIController:
    def __init__(self):
        self.agent_instance = agent.ResumeAgent()
        self.groq_agent = groq_agent.GroqAgent()
    
    async def enhance_resume_section(self, section_name: str, content: str, instructions: str = None) -> Dict[str, Any]:
        """Enhance a specific section of the resume using AI"""
        try:
            # Use the dedicated enhancement function
            enhanced_content = await self.groq_agent.enhance_content(
                section_name=section_name,
                content=content,
                instructions=instructions
            )
            
            return {
                "section": section_name,
                "original": content,
                "enhanced": enhanced_content,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error enhancing content: {str(e)}")